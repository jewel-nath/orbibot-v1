#!/usr/bin/env python3
"""
Safety Features Test Script for OrbiBot Firmware

Tests safety mechanisms:
- Command timeout (motors stop if no command received)
- Emergency stop behavior

IMPORTANT: Robot should be elevated or wheels free to spin!
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode,
    print_header, print_info, print_success, print_error, print_warning, Color
)

# Expected command timeout in firmware (matches COMMAND_TIMEOUT_MS in orbibot_config.h)
COMMAND_TIMEOUT_MS = 2000


def main():
    parser = argparse.ArgumentParser(description='Test safety features')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    args = parser.parse_args()

    print_header("SAFETY FEATURES TEST")
    print_info(f"Port: {args.port}")
    print()
    print_warning("SAFETY: Ensure robot is elevated or wheels are free!")
    print()
    input("Press Enter to start...")

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    timeout_ok = False
    stopped = False

    try:
        proto.enable_auto_report(True)
        time.sleep(0.2)

        # Test 1: Command timeout (firmware stops motors after COMMAND_TIMEOUT_MS with no new command)
        print(f"\n{Color.CYAN}Test 1: Command Timeout{Color.RESET}")
        print(f"  Expected timeout: {COMMAND_TIMEOUT_MS}ms")
        print("  Sending one motion command, then waiting for auto-stop...")
        print()

        # Send forward motion (single command — do not repeat)
        proto.send_motion(0.2, 0, 0)  # 0.2 m/s forward
        print("  [0.0s] Motion command sent (0.2 m/s forward)")
        print("  Motors should be spinning now...")

        # Monitor for COMMAND_TIMEOUT_MS + 1s margin
        monitor_duration = (COMMAND_TIMEOUT_MS / 1000.0) + 1.0
        start = time.time()
        last_speed = None

        while time.time() - start < monitor_duration:
            packets = proto.read_packets(timeout=0.1)
            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_SPEED:
                    data = proto.parse_speed(payload)
                    if data:
                        elapsed = time.time() - start
                        if last_speed != data.vx_mm:
                            if data.vx_mm == 0 and last_speed and last_speed != 0:
                                print(f"  [{elapsed:.1f}s] Motors STOPPED (vx={data.vx_mm})")
                            else:
                                print(f"  [{elapsed:.1f}s] Speed: vx={data.vx_mm} mm/s")
                            last_speed = data.vx_mm

        # Verify timeout occurred
        timeout_ok = (last_speed == 0)
        if timeout_ok:
            print_success("Command timeout working - motors auto-stopped")
        else:
            print_error("Command timeout may not be working!")
            proto.stop()  # Force stop

        # Test 2: Stop command
        print(f"\n{Color.CYAN}Test 2: Stop Command{Color.RESET}")
        print("  Sending motion, then immediate stop...")

        proto.send_motion(0.2, 0, 0)
        time.sleep(0.3)
        proto.stop()
        print("  Stop command sent")

        time.sleep(0.5)
        packets = proto.read_packets(timeout=0.3)
        stopped = False
        for func_code, payload in packets:
            if func_code == FuncCode.REPORT_SPEED:
                data = proto.parse_speed(payload)
                if data and data.vx_mm == 0:
                    stopped = True

        if stopped:
            print_success("Stop command working")
        else:
            print_warning("Could not verify stop (check manually)")

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        proto.stop()

    finally:
        proto.stop()
        proto.enable_auto_report(False)
        proto.disconnect()

    print()
    print_header("SUMMARY")
    print("Safety features verified:")
    print(f"  - Command timeout: {'OK' if timeout_ok else 'VERIFY MANUALLY'}")
    print(f"  - Stop command: {'OK' if stopped else 'VERIFY MANUALLY'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
