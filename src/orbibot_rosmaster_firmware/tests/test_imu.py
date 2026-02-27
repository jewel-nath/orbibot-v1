#!/usr/bin/env python3
"""
IMU Test Script for OrbiBot Firmware

Tests ICM-20948 IMU readings:
- Raw accelerometer and gyroscope data
- Attitude angles (roll, pitch, yaw)

Tilt the robot and verify readings change appropriately.
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode, IMURawData, IMUAttitudeData,
    print_header, print_info, print_success, print_error, print_warning, Color
)


def main():
    parser = argparse.ArgumentParser(description='Test IMU readings')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=float, default=30.0, help='Test duration')
    parser.add_argument('--mode', '-m', choices=['raw', 'attitude', 'both'], default='both',
                        help='Data mode: raw, attitude, or both')
    parser.add_argument('--rate', '-r', type=float, default=2.0, help='Display rate in Hz (default: 2)')
    args = parser.parse_args()

    display_interval = 1.0 / args.rate  # Convert Hz to seconds

    print_header("IMU TEST (ICM-20948)")
    print_info(f"Port: {args.port}")
    print_info(f"Mode: {args.mode}")
    print_info(f"Duration: {args.duration}s")
    print()
    print("Instructions:")
    print("  1. Place robot flat to see baseline readings")
    print("  2. Tilt forward (pitch), sideways (roll), rotate (yaw)")
    print("  3. Verify readings change appropriately")
    print("  4. Press Ctrl+C to stop")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        proto.enable_auto_report(True)
        time.sleep(0.2)

        if args.mode == 'raw':
            print(f"\n{Color.CYAN}=== RAW IMU DATA ==={Color.RESET}")
            print(f"{'Time':>6} | {'GyroX':>8} {'GyroY':>8} {'GyroZ':>8} | {'AccX':>8} {'AccY':>8} {'AccZ':>8}")
            print("-" * 75)
        elif args.mode == 'attitude':
            print(f"\n{Color.CYAN}=== ATTITUDE ANGLES ==={Color.RESET}")
            print(f"{'Time':>6} | {'Roll':>10} | {'Pitch':>10} | {'Yaw':>10}")
            print("-" * 50)
        else:  # both
            print(f"\n{Color.CYAN}=== ATTITUDE ANGLES (update rate: {args.rate} Hz) ==={Color.RESET}")
            print("-" * 55)

        start_time = time.time()
        raw_count = 0
        att_count = 0
        last_print = 0

        # Store latest values for combined display
        latest_raw = None
        latest_att = None

        while time.time() - start_time < args.duration:
            packets = proto.read_packets(timeout=0.1)

            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_IMU_RAW:
                    data = proto.parse_imu_raw(payload)
                    if data:
                        raw_count += 1
                        latest_raw = data

                elif func_code == FuncCode.REPORT_IMU_ATTITUDE:
                    data = proto.parse_imu_attitude(payload)
                    if data:
                        att_count += 1
                        latest_att = data

            # Display at configured rate
            elapsed = time.time() - start_time
            if elapsed - last_print >= display_interval:
                if args.mode == 'raw' and latest_raw:
                    print(f"{elapsed:6.1f} | {latest_raw.gyro_x:8d} {latest_raw.gyro_y:8d} {latest_raw.gyro_z:8d} | "
                          f"{latest_raw.accel_x:8d} {latest_raw.accel_y:8d} {latest_raw.accel_z:8d}")
                elif args.mode == 'attitude' and latest_att:
                    print(f"{elapsed:6.1f} | {latest_att.roll:+10.2f} | {latest_att.pitch:+10.2f} | {latest_att.yaw:+10.2f}")
                elif args.mode == 'both' and latest_att:
                    # Combined single-line display
                    print(f"{elapsed:5.1f}s | Roll: {latest_att.roll:+6.1f}  Pitch: {latest_att.pitch:+6.1f}  Yaw: {latest_att.yaw:+7.1f}")
                last_print = elapsed

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.enable_auto_report(False)
        proto.disconnect()

    # Summary
    print()
    print_header("TEST SUMMARY")
    print_info(f"Raw IMU packets received: {raw_count}")
    print_info(f"Attitude packets received: {att_count}")

    if raw_count > 0 or att_count > 0:
        print_success("IMU is working!")
    else:
        print_error("No IMU data received - check IMU connection")

    print()
    print("Expected behavior:")
    print(f"  {Color.CYAN}Flat:{Color.RESET} AccZ ~ 16000, Roll/Pitch ~ 0")
    print(f"  {Color.CYAN}Tilt forward:{Color.RESET} Pitch increases")
    print(f"  {Color.CYAN}Tilt sideways:{Color.RESET} Roll changes")
    print(f"  {Color.CYAN}Rotate:{Color.RESET} Yaw changes (may drift)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
