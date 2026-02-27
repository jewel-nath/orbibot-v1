#!/usr/bin/env python3
"""
OLED Display Test Script for OrbiBot Firmware

Tests OLED display by sending text to each line.
Display: SSD1306 128x64 (4 lines of 16 characters)
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol,
    print_header, print_info, print_success, print_error, Color
)


def main():
    parser = argparse.ArgumentParser(description='Test OLED display')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--text', '-t', type=str, help='Custom text to display')
    args = parser.parse_args()

    print_header("OLED DISPLAY TEST")
    print_info(f"Port: {args.port}")
    print()
    print("This test sends text to the OLED display.")
    print("Watch the display on the ROSMaster board.")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        # Test 1: Display test pattern
        print(f"{Color.CYAN}Test 1: Test pattern{Color.RESET}")
        lines = [
            "OrbiBot Test",
            "Line 2: ABCDEFGH",
            "Line 3: 12345678",
            "Line 4: ********"
        ]
        for i, text in enumerate(lines):
            proto.set_oled(i, text)
            print(f"  Line {i}: '{text}'")
            time.sleep(0.1)

        print("  Check OLED display...")
        time.sleep(3)

        # Test 2: Counter
        print(f"\n{Color.CYAN}Test 2: Counter (5 seconds){Color.RESET}")
        proto.set_oled(0, "Counter Test")
        proto.set_oled(1, "")
        proto.set_oled(3, "")

        for i in range(5):
            proto.set_oled(2, f"Count: {i+1}")
            print(f"  Count: {i+1}")
            time.sleep(1)

        # Test 3: Custom text or status
        print(f"\n{Color.CYAN}Test 3: Status display{Color.RESET}")
        if args.text:
            proto.set_oled(0, args.text[:16])
            proto.set_oled(1, args.text[16:32] if len(args.text) > 16 else "")
            print(f"  Custom: '{args.text}'")
        else:
            proto.set_oled(0, "OrbiBot Ready")
            proto.set_oled(1, "FW Test Mode")
            proto.set_oled(2, "Batt: --.-V")
            proto.set_oled(3, "Status: OK")
            print("  Displaying status screen")

        time.sleep(2)

        # Test 4: Clear display
        print(f"\n{Color.CYAN}Test 4: Clear display{Color.RESET}")
        for i in range(4):
            proto.set_oled(i, "")
        print("  Display cleared")

        time.sleep(1)

        # Final: Show ready
        proto.set_oled(0, "Test Complete!")
        proto.set_oled(1, "OLED Working")

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.disconnect()

    print()
    print_success("OLED test complete!")
    print("If you saw text on the display, OLED is working correctly.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
