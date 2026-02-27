#!/usr/bin/env python3
"""
Data Rate Test Script for OrbiBot Firmware

Measures firmware communication performance:
- Bytes per second
- Packets per second
- Packet types and frequencies

Expected rates (25Hz auto-report):
- ~25 packets/s per type (speed, encoder, IMU raw, IMU attitude)
- ~100 total packets/s
- ~1000-2000 bytes/s
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode, PacketMonitor,
    print_header, print_info, print_success, print_error, print_warning, Color
)


# Function code names for display
FUNC_NAMES = {
    FuncCode.REPORT_SPEED: 'Speed',
    FuncCode.REPORT_IMU_RAW: 'IMU_Raw',
    FuncCode.REPORT_IMU_ATTITUDE: 'IMU_Att',
    FuncCode.REPORT_ENCODER: 'Encoder',
    FuncCode.REPORT_ODOM: 'Odom',
}


def main():
    parser = argparse.ArgumentParser(description='Test firmware data rate')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=float, default=10.0, help='Test duration')
    args = parser.parse_args()

    print_header("DATA RATE TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Duration: {args.duration}s")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect(timeout=0.01):  # Short timeout for fast reads
        print_error(f"Failed to connect to {args.port}")
        return 1

    monitor = PacketMonitor(proto)

    try:
        print("Enabling auto-report...")
        proto.enable_auto_report(True)
        time.sleep(0.2)

        print("Measuring data rate...")
        print()
        print(f"{'Time':>4} | {'Bytes':>8} | {'Packets':>8} | {'B/s':>8} | {'Pkt/s':>8}")
        print("-" * 50)

        monitor.start()
        last_report = time.time()

        while monitor.elapsed < args.duration:
            monitor.process(timeout=0.05)

            # Print update every second
            if time.time() - last_report >= 1.0:
                print(f"{monitor.elapsed:4.0f} | {monitor.total_bytes:8d} | "
                      f"{monitor.total_packets:8d} | {monitor.byte_rate:8.0f} | "
                      f"{monitor.packet_rate:8.1f}")
                last_report = time.time()

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.enable_auto_report(False)
        proto.disconnect()

    # Final statistics
    print()
    print_header("RESULTS")

    print(f"Total time:        {monitor.elapsed:.1f} seconds")
    print(f"Total bytes:       {monitor.total_bytes}")
    print(f"Total packets:     {monitor.total_packets}")
    print(f"Average byte rate: {monitor.byte_rate:.0f} B/s")
    print(f"Average pkt rate:  {monitor.packet_rate:.1f} pkt/s")
    print()

    print("Packets by type:")
    for func_code, count in sorted(monitor.packet_counts.items()):
        name = FUNC_NAMES.get(func_code, f'0x{func_code:02X}')
        rate = count / monitor.elapsed if monitor.elapsed > 0 else 0
        print(f"  {name:12}: {count:6d} ({rate:5.1f}/s)")

    print()

    # Validate expected rates
    expected_rate = 25.0  # Expected 25Hz per packet type
    issues = []

    for func_code in [FuncCode.REPORT_SPEED, FuncCode.REPORT_ENCODER,
                      FuncCode.REPORT_IMU_RAW, FuncCode.REPORT_IMU_ATTITUDE]:
        count = monitor.packet_counts.get(func_code, 0)
        rate = count / monitor.elapsed if monitor.elapsed > 0 else 0
        name = FUNC_NAMES.get(func_code, f'0x{func_code:02X}')

        if rate < expected_rate * 0.8:  # Allow 20% tolerance
            issues.append(f"{name}: {rate:.1f}/s (expected ~{expected_rate})")

    if issues:
        print_warning("Low packet rates detected:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print_success("All packet rates are normal!")

    # Overall assessment
    if monitor.packet_rate >= 80:  # ~100 expected
        print_success(f"Data rate is GOOD ({monitor.packet_rate:.0f} pkt/s)")
    elif monitor.packet_rate >= 40:
        print_warning(f"Data rate is LOW ({monitor.packet_rate:.0f} pkt/s)")
    else:
        print_error(f"Data rate is VERY LOW ({monitor.packet_rate:.0f} pkt/s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
