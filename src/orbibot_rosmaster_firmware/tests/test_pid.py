#!/usr/bin/env python3
"""
PID Controller Test Script for OrbiBot Firmware

Tests PID parameter configuration and motor velocity control.

This test:
- Reads current PID parameters (if supported)
- Tests velocity control response
- Measures steady-state error
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode,
    print_header, print_info, print_success, print_error, print_warning, Color
)


def main():
    parser = argparse.ArgumentParser(description='Test PID controller')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--speed', '-s', type=float, default=0.2, help='Test speed in m/s')
    parser.add_argument('--duration', '-d', type=float, default=10.0, help='Test duration')
    args = parser.parse_args()

    print_header("PID CONTROLLER TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Target speed: {args.speed} m/s ({args.speed*1000:.0f} mm/s)")
    print_info(f"Duration: {args.duration}s")
    print()
    print_warning("SAFETY: Ensure robot is elevated or wheels are free!")
    print()
    input("Press Enter to start...")

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    target_mm = int(args.speed * 1000)
    measured_speeds = []

    try:
        proto.enable_auto_report(True)
        time.sleep(0.2)

        print(f"\n{Color.CYAN}Velocity Control Test{Color.RESET}")
        print(f"Target: {target_mm} mm/s forward")
        print()
        print(f"{'Time':>6} | {'Target':>8} | {'Measured':>8} | {'Error':>8} | {'Error %':>8}")
        print("-" * 55)

        # Send motion command
        proto.send_motion(args.speed, 0, 0)
        start = time.time()
        last_print = 0

        while time.time() - start < args.duration:
            # Keep sending commands to maintain motion
            if (time.time() - start) % 0.1 < 0.01:
                proto.send_motion(args.speed, 0, 0)

            packets = proto.read_packets(timeout=0.05)
            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_SPEED:
                    data = proto.parse_speed(payload)
                    if data:
                        elapsed = time.time() - start
                        measured = data.vx_mm
                        error = measured - target_mm
                        error_pct = (error / target_mm * 100) if target_mm != 0 else 0

                        # Skip first 0.5s (ramp-up time)
                        if elapsed > 0.5:
                            measured_speeds.append(measured)

                        if elapsed - last_print >= 0.5:
                            print(f"{elapsed:6.1f} | {target_mm:8d} | {measured:8d} | {error:+8d} | {error_pct:+7.1f}%")
                            last_print = elapsed

        # Stop
        proto.stop()

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        proto.stop()

    finally:
        proto.stop()
        proto.enable_auto_report(False)
        proto.disconnect()

    # Analysis
    print()
    print_header("ANALYSIS")

    if measured_speeds:
        avg_speed = sum(measured_speeds) / len(measured_speeds)
        min_speed = min(measured_speeds)
        max_speed = max(measured_speeds)
        avg_error = avg_speed - target_mm
        avg_error_pct = (avg_error / target_mm * 100) if target_mm != 0 else 0

        print(f"Samples: {len(measured_speeds)}")
        print(f"Target:  {target_mm} mm/s")
        print(f"Average: {avg_speed:.0f} mm/s")
        print(f"Min:     {min_speed} mm/s")
        print(f"Max:     {max_speed} mm/s")
        print(f"Avg error: {avg_error:+.0f} mm/s ({avg_error_pct:+.1f}%)")
        print()

        if abs(avg_error_pct) < 10:
            print_success("PID control is good (error < 10%)")
        elif abs(avg_error_pct) < 20:
            print_warning("PID control is acceptable (error 10-20%)")
        else:
            print_error("PID control needs tuning (error > 20%)")
    else:
        print_error("No speed measurements collected")

    return 0


if __name__ == "__main__":
    sys.exit(main())
