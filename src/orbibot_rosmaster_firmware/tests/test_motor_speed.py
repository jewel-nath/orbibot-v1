#!/usr/bin/env python3
"""
Motor Speed Control Test Script for OrbiBot Firmware

Interactive test for robot motion control.
Uses velocity commands (vx, vy, vz) to test mecanum kinematics.

Controls:
- WASD: Forward/Backward/Left/Right strafe
- QE: Rotate CCW/CW
- 1-9: Speed multiplier
- Space: Stop
"""

import sys
import time
import argparse
import select
import tty
import termios
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode,
    print_header, print_info, print_success, print_error, Color
)


def get_key():
    """Get single keypress without blocking."""
    if select.select([sys.stdin], [], [], 0.01)[0]:
        return sys.stdin.read(1).lower()
    return None


def main():
    parser = argparse.ArgumentParser(description='Interactive motor speed control test')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    args = parser.parse_args()

    print_header("MOTOR SPEED CONTROL TEST")
    print_info(f"Port: {args.port}")
    print()
    print("Controls:")
    print(f"  {Color.CYAN}W/S{Color.RESET} - Forward/Backward")
    print(f"  {Color.CYAN}A/D{Color.RESET} - Left/Right strafe")
    print(f"  {Color.CYAN}Q/E{Color.RESET} - Rotate CCW/CW")
    print(f"  {Color.CYAN}1-9{Color.RESET} - Speed: 0.1-0.9 m/s")
    print(f"  {Color.CYAN}Space{Color.RESET} - Stop")
    print(f"  {Color.CYAN}Esc/X{Color.RESET} - Quit")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    # Set terminal to raw mode for single character input
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)

        proto.enable_auto_report(True)
        time.sleep(0.2)

        speed = 0.2  # Default speed in m/s
        rot_speed = 0.5  # Rotation speed in rad/s
        current_vx = 0
        current_vy = 0
        current_vz = 0

        print(f"Speed: {speed:.1f} m/s | Rotation: {rot_speed:.1f} rad/s")
        print("-" * 50)

        running = True
        last_status_time = time.time()

        while running:
            # Check for keypress
            key = get_key()

            if key:
                vx, vy, vz = 0, 0, 0

                if key == 'w':
                    vx = speed
                    print(f"\rForward: {vx*1000:.0f} mm/s" + " " * 30, end='')
                elif key == 's':
                    vx = -speed
                    print(f"\rBackward: {abs(vx)*1000:.0f} mm/s" + " " * 30, end='')
                elif key == 'a':
                    vy = speed
                    print(f"\rLeft strafe: {vy*1000:.0f} mm/s" + " " * 30, end='')
                elif key == 'd':
                    vy = -speed
                    print(f"\rRight strafe: {abs(vy)*1000:.0f} mm/s" + " " * 30, end='')
                elif key == 'q':
                    vz = rot_speed
                    print(f"\rRotate CCW: {vz*1000:.0f} mrad/s" + " " * 30, end='')
                elif key == 'e':
                    vz = -rot_speed
                    print(f"\rRotate CW: {abs(vz)*1000:.0f} mrad/s" + " " * 30, end='')
                elif key == ' ':
                    print(f"\rSTOP" + " " * 40, end='')
                elif key in '123456789':
                    speed = int(key) * 0.1
                    print(f"\rSpeed set to {speed:.1f} m/s" + " " * 30, end='')
                    continue
                elif key == '\x1b' or key == 'x':  # Escape or x
                    print("\rQuitting..." + " " * 40)
                    running = False
                    continue
                else:
                    continue

                current_vx, current_vy, current_vz = vx, vy, vz
                proto.send_motion(vx, vy, vz)

            # Read and display feedback
            packets = proto.read_packets(timeout=0.01)
            for func_code, payload in packets:
                if func_code == FuncCode.REPORT_SPEED:
                    data = proto.parse_speed(payload)
                    if data and time.time() - last_status_time > 0.5:
                        status = f"\r[Measured] vx={data.vx_mm:+4d} vy={data.vy_mm:+4d} vz={data.vz_mrad:+4d} | Batt={data.battery_v:.1f}V"
                        print(status + " " * 10, end='')
                        last_status_time = time.time()

    except KeyboardInterrupt:
        print("\n\nInterrupted.")

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        proto.stop()
        proto.enable_auto_report(False)
        proto.disconnect()
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
