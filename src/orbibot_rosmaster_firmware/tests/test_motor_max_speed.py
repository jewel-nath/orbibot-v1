#!/usr/bin/env python3
"""
Per-Motor Max Speed Measurement for OrbiBot

Drives the robot forward at maximum velocity (wheels off ground) and reads
per-motor encoder deltas to determine each motor's actual max speed.

lgdxrobot2 found 23% variation between 4 motors — this test quantifies OrbiBot's.

SAFETY: Wheels must be OFF the ground before running this test!

Usage:
  python3 test_motor_max_speed.py [--port /dev/motordriver] [--duration 5]
"""

import sys
import time
import argparse
import statistics
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode,
    print_header, print_info, print_success, print_error, print_warning, Color
)

MOTOR_NAMES = ['M1 (FL)', 'M2 (BL)', 'M3 (FR)', 'M4 (BR)']
WHEEL_RADIUS_M = 0.05
ENCODER_PPR = 1320
WHEEL_CIRC_MM = 2 * 3.14159265 * WHEEL_RADIUS_M * 1000  # ~314.16 mm


def collect_encoder_speeds(proto, duration_s, vx=0.0, vy=0.0, vz=0.0):
    """Collect per-motor speeds from encoder reports over a duration.

    Keeps sending motion commands every 200ms to prevent firmware timeout (2s).

    Returns:
        dict: motor_id → list of speed_mms samples
    """
    motor_speeds = {i: [] for i in range(4)}
    last_enc = None
    last_time = None
    last_cmd_time = 0

    start = time.time()
    while time.time() - start < duration_s:
        now = time.time()

        # Re-send motion command every 200ms to prevent firmware timeout
        if now - last_cmd_time > 0.2:
            proto.send_motion(vx, vy, vz)
            last_cmd_time = now

        packets = proto.read_packets(timeout=0.02)
        now = time.time()
        for func_code, payload in packets:
            if func_code == FuncCode.REPORT_ENCODER:
                enc = proto.parse_encoder(payload)
                if enc and last_enc and last_time:
                    dt = now - last_time
                    if dt > 0.005:  # Min 5ms between samples
                        enc_vals = [enc.m1, enc.m2, enc.m3, enc.m4]
                        last_vals = [last_enc.m1, last_enc.m2, last_enc.m3, last_enc.m4]
                        for i in range(4):
                            delta = enc_vals[i] - last_vals[i]
                            # Handle int32 wraparound
                            if abs(delta) > 2**30:
                                continue
                            speed_mms = abs(delta / ENCODER_PPR * WHEEL_CIRC_MM / dt)
                            if speed_mms < 5000:  # Sanity: < 5 m/s
                                motor_speeds[i].append(speed_mms)
                last_enc = enc
                last_time = now
    return motor_speeds


def filter_outliers(samples, sigma=2.0):
    """Remove samples outside mean ± sigma*std."""
    if len(samples) < 10:
        return samples
    mean = statistics.mean(samples)
    std = statistics.stdev(samples)
    filtered = [s for s in samples if abs(s - mean) < sigma * std]
    return filtered if len(filtered) > 5 else samples


def main():
    parser = argparse.ArgumentParser(description='Measure per-motor max speed')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--duration', '-d', type=float, default=5.0,
                        help='Measurement duration (seconds, after ramp-up)')
    parser.add_argument('--speed', '-s', type=float, default=1.0,
                        help='Target speed m/s (use 1.0 to saturate motors)')
    args = parser.parse_args()

    print_header("PER-MOTOR MAX SPEED MEASUREMENT")
    print_info(f"Port: {args.port}")
    print_info(f"Duration: {args.duration}s measurement (+ 2s ramp)")
    print_info(f"Target: {args.speed} m/s forward")
    print()
    print_warning("SAFETY: Wheels must be OFF the ground!")
    print()

    response = input("Wheels off ground? Continue? [y/N] ")
    if response.lower() != 'y':
        print("Aborted.")
        return 1

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        proto.enable_auto_report(True)
        time.sleep(0.3)

        # === Test 1: Full speed forward (all 4 motors same direction) ===
        print(f'\n{Color.CYAN}Test: Full speed forward ({args.speed} m/s){Color.RESET}')
        print('  Ramp-up (2s)...', end='', flush=True)
        # Ramp-up: keep sending command while draining packets
        ramp_start = time.time()
        while time.time() - ramp_start < 2.0:
            proto.send_motion(args.speed, 0.0, 0.0)
            proto.read_packets(timeout=0.05)
        print(' done. Measuring...', end='', flush=True)

        fwd_speeds = collect_encoder_speeds(proto, args.duration,
                                            vx=args.speed, vy=0.0, vz=0.0)
        proto.stop()
        time.sleep(0.5)
        print(' done.')

        # === Results ===
        print('\n' + '=' * 70)
        print('RESULTS — Forward motion (all motors engaged)')
        print('=' * 70)
        print(f'{"Motor":<12} {"Avg (mm/s)":>12} {"Avg (rad/s)":>12} {"Max (mm/s)":>12} {"Std":>8} {"N":>6}')
        print('-' * 70)

        valid_avgs = []
        valid_maxes = []
        motor_results = {}

        for motor_id in range(4):
            samples = fwd_speeds[motor_id]
            if not samples:
                print(f'{MOTOR_NAMES[motor_id]:<12} {"NO DATA":>12}')
                continue

            samples = filter_outliers(samples)
            avg = statistics.mean(samples)
            std = statistics.stdev(samples) if len(samples) > 1 else 0
            max_val = max(samples)
            rad_s = avg / (WHEEL_RADIUS_M * 1000)

            motor_results[motor_id] = {'avg': avg, 'std': std, 'max': max_val, 'rad_s': rad_s}
            valid_avgs.append(avg)
            valid_maxes.append(max_val)

            print(f'{MOTOR_NAMES[motor_id]:<12} {avg:>12.1f} {rad_s:>12.2f} {max_val:>12.1f} {std:>8.1f} {len(samples):>6d}')

        if valid_avgs:
            fastest = max(valid_avgs)
            slowest = min(valid_avgs)
            variation = (fastest - slowest) / fastest * 100 if fastest > 0 else 0

            print()
            print(f'  Fastest motor: {fastest:.0f} mm/s ({fastest/(WHEEL_RADIUS_M*1000):.2f} rad/s)')
            print(f'  Slowest motor: {slowest:.0f} mm/s ({slowest/(WHEEL_RADIUS_M*1000):.2f} rad/s)')
            print(f'  Variation:     {variation:.1f}%')

            recommended_max = max(valid_maxes) * 2.0
            print()
            print('  Recommended for orbibot_config.h:')
            print(f'    #define MAX_WHEEL_SPEED_MMS  {recommended_max:.0f}f  // 2x measured max')
            print()
            print('  Per-motor measured speeds:')
            for motor_id in range(4):
                r = motor_results.get(motor_id)
                if r:
                    print(f'    // {MOTOR_NAMES[motor_id]}: avg={r["avg"]:.0f} mm/s, max={r["max"]:.0f} mm/s ({r["rad_s"]:.2f} rad/s)')
        else:
            print_error("No encoder data received! Check encoder wiring.")

        print('=' * 70)

    except KeyboardInterrupt:
        print("\n\nInterrupted — stopping motors.")

    finally:
        proto.stop()
        time.sleep(0.2)
        proto.enable_auto_report(False)
        proto.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
