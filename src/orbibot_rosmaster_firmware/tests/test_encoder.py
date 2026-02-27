#!/usr/bin/env python3
"""
Encoder Test Script for OrbiBot Firmware

Tests encoder readings from all 4 motors.
Manually rotate each wheel and verify:
- Forward rotation = positive delta
- Backward rotation = negative delta

Motor mapping:
- M1: Front-Left (FL)
- M2: Back-Left (BL)
- M3: Front-Right (FR)
- M4: Back-Right (BR)
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode, EncoderData,
    print_header, print_info, print_success, print_error, Color
)


def main():
    parser = argparse.ArgumentParser(description='Test encoder readings')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=float, default=30.0, help='Test duration in seconds')
    parser.add_argument('--rate', '-r', type=float, default=2.0, help='Max display rate in Hz (default: 2)')
    parser.add_argument('--change-only', '-c', action='store_true', help='Only show when values change')
    args = parser.parse_args()

    display_interval = 1.0 / args.rate

    print_header("ENCODER TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Duration: {args.duration}s")
    print_info(f"Display rate: {args.rate} Hz")
    print()
    print("Instructions:")
    print("  1. Manually rotate each wheel FORWARD (robot moves forward)")
    print("  2. Verify delta is POSITIVE")
    print("  3. Rotate BACKWARD and verify delta is NEGATIVE")
    print("  4. Press Ctrl+C to stop")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        proto.enable_auto_report(True)
        time.sleep(0.2)

        print(f"{'Time':>6} | {'M1 (FL)':>10} | {'M2 (BL)':>10} | {'M3 (FR)':>10} | {'M4 (BR)':>10} | {'Delta'}")
        print("-" * 80)

        last_enc = None
        last_print_enc = None
        start_time = time.time()
        last_print_time = 0
        packet_count = 0

        while time.time() - start_time < args.duration:
            packets = proto.read_packets(timeout=0.1)

            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_ENCODER:
                    enc = proto.parse_encoder(payload)
                    if enc:
                        packet_count += 1
                        last_enc = enc

            # Check if we should display
            elapsed = time.time() - start_time
            if last_enc and elapsed - last_print_time >= display_interval:
                # Calculate delta from last printed value
                delta_str = ""
                has_change = False
                if last_print_enc:
                    deltas = [
                        last_enc.m1 - last_print_enc.m1,
                        last_enc.m2 - last_print_enc.m2,
                        last_enc.m3 - last_print_enc.m3,
                        last_enc.m4 - last_print_enc.m4
                    ]
                    has_change = any(d != 0 for d in deltas)
                    if has_change:
                        parts = []
                        for d in deltas:
                            if d > 0:
                                parts.append(f"{Color.GREEN}{d:+d}{Color.RESET}")
                            elif d < 0:
                                parts.append(f"{Color.RED}{d:+d}{Color.RESET}")
                            else:
                                parts.append(f"{d:+d}")
                        delta_str = f"[{', '.join(parts)}]"

                # Only print if change detected or not in change-only mode
                if not args.change_only or has_change or last_print_enc is None:
                    print(f"{elapsed:6.1f} | {last_enc.m1:10d} | {last_enc.m2:10d} | {last_enc.m3:10d} | {last_enc.m4:10d} | {delta_str}")
                    last_print_enc = EncoderData(last_enc.m1, last_enc.m2, last_enc.m3, last_enc.m4)
                    last_print_time = elapsed

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.enable_auto_report(False)
        proto.disconnect()

    print()
    print_info(f"Received {packet_count} encoder packets")
    print()
    print("Expected behavior:")
    print(f"  {Color.GREEN}Forward rotation = POSITIVE delta{Color.RESET}")
    print(f"  {Color.RED}Backward rotation = NEGATIVE delta{Color.RESET}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
