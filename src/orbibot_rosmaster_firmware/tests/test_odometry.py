#!/usr/bin/env python3
"""
Odometry Test Script for OrbiBot Firmware

Tests odometry/position tracking by monitoring encoder integration.

This test verifies:
- Encoder counts accumulate correctly
- Position estimation from wheel rotations
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode, EncoderData,
    print_header, print_info, print_success, print_error, print_warning, Color
)

# Robot parameters (adjust for your robot)
WHEEL_DIAMETER_M = 0.065  # 65mm mecanum wheels
ENCODER_CPR = 330         # Counts per revolution
WHEEL_BASE_M = 0.15       # Distance between left/right wheels


def encoder_to_distance(counts: int) -> float:
    """Convert encoder counts to distance in meters."""
    import math
    wheel_circumference = math.pi * WHEEL_DIAMETER_M
    revolutions = counts / ENCODER_CPR
    return revolutions * wheel_circumference


def main():
    parser = argparse.ArgumentParser(description='Test odometry')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=float, default=30.0, help='Test duration')
    args = parser.parse_args()

    print_header("ODOMETRY TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Duration: {args.duration}s")
    print()
    print("Robot parameters:")
    print(f"  Wheel diameter: {WHEEL_DIAMETER_M*1000:.0f}mm")
    print(f"  Encoder CPR: {ENCODER_CPR}")
    print(f"  Wheel base: {WHEEL_BASE_M*1000:.0f}mm")
    print()
    print("Instructions:")
    print("  1. Push robot forward/backward manually")
    print("  2. Observe distance calculation")
    print("  3. Verify against measured distance")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        proto.enable_auto_report(True)
        time.sleep(0.2)

        print(f"{'Time':>6} | {'Left (m)':>10} | {'Right (m)':>10} | {'Avg (m)':>10}")
        print("-" * 50)

        start_time = time.time()
        initial_enc = None
        last_print = 0

        while time.time() - start_time < args.duration:
            packets = proto.read_packets(timeout=0.1)

            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_ENCODER:
                    enc = proto.parse_encoder(payload)
                    if enc:
                        if initial_enc is None:
                            initial_enc = EncoderData(enc.m1, enc.m2, enc.m3, enc.m4)
                            print_info("Initial encoder values captured")

                        elapsed = time.time() - start_time
                        if elapsed - last_print >= 0.5:
                            # Calculate distance for each side
                            # Left side: M1 (FL) + M2 (BL)
                            left_counts = ((enc.m1 - initial_enc.m1) +
                                          (enc.m2 - initial_enc.m2)) / 2
                            # Right side: M3 (FR) + M4 (BR)
                            right_counts = ((enc.m3 - initial_enc.m3) +
                                           (enc.m4 - initial_enc.m4)) / 2

                            left_dist = encoder_to_distance(left_counts)
                            right_dist = encoder_to_distance(right_counts)
                            avg_dist = (left_dist + right_dist) / 2

                            print(f"{elapsed:6.1f} | {left_dist:+10.3f} | {right_dist:+10.3f} | {avg_dist:+10.3f}")
                            last_print = elapsed

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.enable_auto_report(False)
        proto.disconnect()

    print()
    print_header("SUMMARY")
    print("To verify accuracy:")
    print("  1. Mark starting position")
    print("  2. Push robot a known distance (e.g., 1 meter)")
    print("  3. Compare 'Avg' column to actual distance")
    print()
    print("Expected accuracy: within 5% for short distances")

    return 0


if __name__ == "__main__":
    sys.exit(main())
