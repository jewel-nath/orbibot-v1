#!/usr/bin/env python3
"""
Motor Direction Test Script for OrbiBot Firmware

Tests each motor individually to verify direction is correct.
Each motor should spin FORWARD (wheel moves forward when touching ground).

Motor mapping:
- M1: Front-Left (FL) - should spin to move robot forward
- M2: Back-Left (BL) - should spin to move robot forward
- M3: Front-Right (FR) - should spin to move robot forward
- M4: Back-Right (BR) - should spin to move robot forward
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol,
    print_header, print_info, print_success, print_error, print_warning, Color
)


def test_motor(proto: ROSMasterProtocol, motor_id: int, name: str, speed: int = 50, duration: float = 2.0):
    """Test a single motor."""
    print(f"\n{Color.CYAN}Testing {name} (M{motor_id+1})...{Color.RESET}")
    print(f"  Speed: {speed}%")
    print(f"  Duration: {duration}s")
    print("  Wheel should spin FORWARD (robot moves forward direction)")

    # Set motor speed
    proto.set_motor(motor_id, speed)

    # Wait for duration
    time.sleep(duration)

    # Stop motor
    proto.set_motor(motor_id, 0)

    # Ask for confirmation
    print()
    response = input(f"  Did {name} spin FORWARD? [y/n/skip]: ").strip().lower()
    if response == 'y':
        print_success(f"{name} direction is CORRECT")
        return True
    elif response == 'n':
        print_error(f"{name} direction is WRONG - needs inversion")
        return False
    else:
        print_warning(f"{name} test skipped")
        return None


def main():
    parser = argparse.ArgumentParser(description='Test motor directions')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--speed', '-s', type=int, default=30, help='Motor speed (10-100)')
    parser.add_argument('--duration', '-d', type=float, default=2.0, help='Test duration per motor')
    parser.add_argument('--motor', '-m', type=int, choices=[1, 2, 3, 4], help='Test specific motor only')
    args = parser.parse_args()

    print_header("MOTOR DIRECTION TEST")
    print_info(f"Port: {args.port}")
    print_info(f"Speed: {args.speed}%")
    print_info(f"Duration: {args.duration}s per motor")
    print()
    print_warning("SAFETY: Ensure robot is elevated or wheels are free to spin!")
    print()
    input("Press Enter to start...")

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    motors = [
        (0, "Front-Left (FL)"),
        (1, "Back-Left (BL)"),
        (2, "Front-Right (FR)"),
        (3, "Back-Right (BR)")
    ]

    results = {}

    try:
        for motor_id, name in motors:
            if args.motor and (motor_id + 1) != args.motor:
                continue

            result = test_motor(proto, motor_id, name, args.speed, args.duration)
            results[name] = result

            # Brief pause between motors
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        proto.stop()

    finally:
        proto.stop()
        proto.disconnect()

    # Summary
    print_header("TEST RESULTS")

    correct = sum(1 for r in results.values() if r is True)
    wrong = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    for name, result in results.items():
        if result is True:
            print_success(f"{name}: CORRECT")
        elif result is False:
            print_error(f"{name}: WRONG")
        else:
            print_warning(f"{name}: SKIPPED")

    print()
    print(f"Summary: {correct} correct, {wrong} wrong, {skipped} skipped")

    if wrong > 0:
        print()
        print_warning("Motors with wrong direction need inversion in hal_timer.c")
        print("See motor direction inversion in case 0/1/2/3 of hal_timer_set_motor_pwm()")

    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
