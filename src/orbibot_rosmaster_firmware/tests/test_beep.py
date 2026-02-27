#!/usr/bin/env python3
"""
Beep Test Script for OrbiBot Firmware

Tests the buzzer on the ROSMaster board.
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol,
    print_header, print_info, print_success, print_error, Color
)


def main():
    parser = argparse.ArgumentParser(description='Test buzzer')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=int, default=100, help='Beep duration in ms')
    parser.add_argument('--count', '-c', type=int, default=3, help='Number of beeps')
    args = parser.parse_args()

    print_header("BUZZER TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Duration: {args.duration}ms")
    print_info(f"Count: {args.count}")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        print("Listen for beeps from the ROSMaster board...")
        print()

        for i in range(args.count):
            print(f"  Beep {i+1}/{args.count}")
            proto.beep(args.duration)
            time.sleep(args.duration / 1000.0 + 0.3)  # Wait for beep + pause

        print()

        # Pattern test
        print(f"{Color.CYAN}Pattern test: Short-Short-Long{Color.RESET}")
        proto.beep(50)
        time.sleep(0.15)
        proto.beep(50)
        time.sleep(0.15)
        proto.beep(200)
        time.sleep(0.4)

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.disconnect()

    print()
    print_success("Beep test complete!")
    print("If you heard beeps, the buzzer is working correctly.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
