#!/usr/bin/env python3
"""
Battery Voltage Test Script for OrbiBot Firmware

Monitors battery voltage and checks against thresholds.

Voltage thresholds (4S LiFePO4):
- Full: ~14.6V
- Normal: 12.8-14.6V
- Warning: 11.0-12.8V
- Critical: <11.0V  → firmware emergency stop at 10.5V
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode, SpeedData,
    print_header, print_info, print_success, print_error, print_warning, Color
)


# Voltage thresholds — 4S LiFePO4 (matches hardware_params.yaml)
VOLTAGE_FULL = 14.6       # Full charge
VOLTAGE_NORMAL = 12.8     # Nominal operating voltage
VOLTAGE_WARNING = 11.0    # Low warning (hardware_params: battery_low_threshold)
VOLTAGE_CRITICAL = 10.5   # Emergency stop (hardware_params: battery_critical_voltage)


def get_voltage_status(voltage: float) -> tuple:
    """Get status color and message for voltage."""
    if voltage >= VOLTAGE_FULL:
        return Color.GREEN, "FULL"
    elif voltage >= VOLTAGE_NORMAL:
        return Color.GREEN, "NORMAL"
    elif voltage >= VOLTAGE_WARNING:
        return Color.YELLOW, "WARNING"
    elif voltage >= VOLTAGE_CRITICAL:
        return Color.RED, "LOW"
    else:
        return Color.RED, "CRITICAL"


def main():
    parser = argparse.ArgumentParser(description='Monitor battery voltage')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=float, default=30.0, help='Monitor duration')
    parser.add_argument('--interval', '-i', type=float, default=1.0, help='Display interval')
    args = parser.parse_args()

    print_header("BATTERY VOLTAGE TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Duration: {args.duration}s")
    print()
    print("Voltage thresholds (4S LiFePO4):")
    print(f"  {Color.GREEN}Full:     >= {VOLTAGE_FULL}V{Color.RESET}")
    print(f"  {Color.GREEN}Normal:   {VOLTAGE_NORMAL}V - {VOLTAGE_FULL}V{Color.RESET}")
    print(f"  {Color.YELLOW}Warning:  {VOLTAGE_WARNING}V - {VOLTAGE_NORMAL}V{Color.RESET}")
    print(f"  {Color.RED}Critical: < {VOLTAGE_WARNING}V (emergency stop at {VOLTAGE_CRITICAL}V){Color.RESET}")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        proto.enable_auto_report(True)
        time.sleep(0.2)

        print(f"{'Time':>6} | {'Voltage':>10} | {'Status':>10} | {'Bar'}")
        print("-" * 55)

        start_time = time.time()
        last_print = 0
        readings = []
        min_v = 999
        max_v = 0

        while time.time() - start_time < args.duration:
            packets = proto.read_packets(timeout=0.1)

            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_SPEED:
                    data = proto.parse_speed(payload)
                    if data:
                        voltage = data.battery_v
                        readings.append(voltage)
                        min_v = min(min_v, voltage)
                        max_v = max(max_v, voltage)

                        elapsed = time.time() - start_time
                        if elapsed - last_print >= args.interval:
                            color, status = get_voltage_status(voltage)

                            # Create bar graph (10-15V range for 4S LiFePO4)
                            bar_len = int((voltage - 10.0) / 5.0 * 20)
                            bar_len = max(0, min(20, bar_len))
                            bar = '#' * bar_len + '.' * (20 - bar_len)

                            print(f"{elapsed:6.1f} | {color}{voltage:10.2f}V{Color.RESET} | "
                                  f"{color}{status:>10}{Color.RESET} | [{bar}]")
                            last_print = elapsed

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.enable_auto_report(False)
        proto.disconnect()

    # Summary
    print()
    print_header("SUMMARY")

    if readings:
        avg_v = sum(readings) / len(readings)
        color, status = get_voltage_status(avg_v)

        print_info(f"Readings: {len(readings)}")
        print_info(f"Average:  {avg_v:.2f}V")
        print_info(f"Min:      {min_v:.2f}V")
        print_info(f"Max:      {max_v:.2f}V")
        print()

        if avg_v >= VOLTAGE_NORMAL:
            print_success(f"Battery status: {status}")
        elif avg_v >= VOLTAGE_WARNING:
            print_warning(f"Battery status: {status} - consider charging")
        else:
            print_error(f"Battery status: {status} - charge immediately!")
    else:
        print_error("No battery readings received")

    return 0


if __name__ == "__main__":
    sys.exit(main())
