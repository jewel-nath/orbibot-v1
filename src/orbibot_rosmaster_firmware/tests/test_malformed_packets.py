#!/usr/bin/env python3
"""
Malformed Packet Handling — verifies firmware deep-dive finding DD-1.

DD-1 (HIGH): protocol command handlers don't validate payload length.
A packet with `LEN=3, FUNC=0x12/0x13/0x14/0x16/0x01` and a valid checksum is
accepted; the handler reads `data[N]` past the actual payload into stale RAM.

This script crafts checksum-valid truncated packets for each at-risk function
code and observes the firmware's externally visible behaviour:

  - REPORT_SPEED stream still flowing       (no crash, watchdog not tripped)
  - vx/vy/vz from REPORT_SPEED stays at 0   (no rogue motion command)
  - Auto-report rate steady across the test (no flash-save stall ~50 ms)
  - g_unknown_cmd_count is internal (no diag packet); we infer from
    "no observable side effects" that the dispatch was either clean-rejected
    or that stale RAM happened to be benign at the moment of the test.

SAFETY: No motion commands sent. Robot wheels can be on the ground.

Usage:
  python3 test_malformed_packets.py [--port /dev/motordriver]
"""

import argparse
import statistics
import sys
import time

from rosmaster_protocol import (
    HEAD,
    DEVICE_ID,
    COMPLEMENT,
    FuncCode,
    ROSMasterProtocol,
    Color,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)


def make_truncated(func_code: int) -> bytes:
    """Build a [HEAD, DEVICE_ID, LEN=3, FUNC, CKSUM] packet (no payload)."""
    pkt = [HEAD, DEVICE_ID, 0x03, func_code]
    pkt.append(sum(pkt, COMPLEMENT) & 0xFF)
    return bytes(pkt)


def measure_baseline(proto: ROSMasterProtocol, duration_s: float = 2.0) -> dict:
    """Sample REPORT_SPEED for the duration. Return rate + max |vx/vy/vz|."""
    speed_count = 0
    enc_count = 0
    imu_count = 0
    odom_count = 0
    max_vx = max_vy = max_vz = 0
    t0 = time.time()
    while time.time() - t0 < duration_s:
        for fc, payload in proto.read_packets(timeout=0.05):
            if fc == FuncCode.REPORT_SPEED:
                speed_count += 1
                s = proto.parse_speed(payload)
                if s:
                    max_vx = max(max_vx, abs(s.vx_mm))
                    max_vy = max(max_vy, abs(s.vy_mm))
                    max_vz = max(max_vz, abs(s.vz_mrad))
            elif fc == FuncCode.REPORT_ENCODER:
                enc_count += 1
            elif fc == FuncCode.REPORT_IMU_RAW:
                imu_count += 1
            elif fc == FuncCode.REPORT_ODOM:
                odom_count += 1
    elapsed = time.time() - t0
    return {
        'speed_hz': speed_count / elapsed,
        'enc_hz': enc_count / elapsed,
        'imu_hz': imu_count / elapsed,
        'odom_hz': odom_count / elapsed,
        'max_vx_mm': max_vx,
        'max_vy_mm': max_vy,
        'max_vz_mrad': max_vz,
    }


def main():
    parser = argparse.ArgumentParser(description='Malformed packet handling test (DD-1)')
    parser.add_argument('--port', '-p', default='/dev/motordriver')
    parser.add_argument('--blasts', '-n', type=int, default=20,
                        help='Number of malformed packets per function code')
    args = parser.parse_args()

    print_header("DD-1: Malformed Packet (truncated payload) handling")
    print_info(f"Port:    {args.port}")
    print_info(f"Per FC:  {args.blasts} malformed packets")
    print_warning("Verifies firmware does not move motors or stall on truncated cmds.")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    target_funcs = [
        ('FUNC_AUTO_REPORT  (0x01)', FuncCode.AUTO_REPORT),
        ('FUNC_MOTION       (0x12)', FuncCode.MOTION),
        ('FUNC_SET_MOTOR_PID(0x13)', FuncCode.SET_MOTOR_PID),
        ('FUNC_SET_YAW_PID  (0x14)', FuncCode.SET_YAW_PID),
    ]

    rc = 0
    try:
        proto.enable_auto_report(True)
        time.sleep(0.3)
        proto.ser.reset_input_buffer()

        # --- 1. Baseline ---
        print(f'{Color.CYAN}Step 1: Baseline 2 s of auto-report{Color.RESET}')
        base = measure_baseline(proto, 2.0)
        print(f'  REPORT_SPEED   : {base["speed_hz"]:.1f} Hz')
        print(f'  REPORT_ENCODER : {base["enc_hz"]:.1f} Hz')
        print(f'  REPORT_IMU_RAW : {base["imu_hz"]:.1f} Hz')
        print(f'  REPORT_ODOM    : {base["odom_hz"]:.1f} Hz')
        print(f'  max |vx,vy,vz| : {base["max_vx_mm"]} / {base["max_vy_mm"]} / '
              f'{base["max_vz_mrad"]} (mm/s, mm/s, mrad/s)')
        if base['speed_hz'] < 30:
            print_error("Baseline rate too low — auto-report not flowing")
            return 1
        if base['max_vx_mm'] or base['max_vy_mm'] or base['max_vz_mrad']:
            print_warning("Robot wasn't fully stationary during baseline")
        print()

        # --- 2. Blast each at-risk func code ---
        rates = []
        for label, fc in target_funcs:
            print(f'{Color.CYAN}Step 2: Blast {args.blasts}× {label}{Color.RESET}')
            pkt = make_truncated(int(fc))
            proto.ser.reset_input_buffer()
            send_t0 = time.time()
            for _ in range(args.blasts):
                proto.ser.write(pkt)
                time.sleep(0.005)  # 5 ms between sends; faster than 50 Hz frame
            send_elapsed = time.time() - send_t0

            # Watch for 1.5 s after the blast
            after = measure_baseline(proto, 1.5)
            rates.append((label, after))

            print(f'  sent {args.blasts} pkts in {send_elapsed*1000:.0f} ms')
            print(f'  post-blast rates  : speed={after["speed_hz"]:.1f}  '
                  f'enc={after["enc_hz"]:.1f}  imu={after["imu_hz"]:.1f}  '
                  f'odom={after["odom_hz"]:.1f} Hz')
            print(f'  post-blast motion : vx={after["max_vx_mm"]} '
                  f'vy={after["max_vy_mm"]} vz={after["max_vz_mrad"]}')

            # --- Verdict per function code ---
            speed_drop = base['speed_hz'] - after['speed_hz']
            if after['speed_hz'] < 0.6 * base['speed_hz']:
                print_error(f"  STREAM DEGRADED — speed rate dropped by "
                            f"{speed_drop:.1f} Hz (was {base['speed_hz']:.1f}). "
                            "Possible flash-save stall or watchdog miss.")
                rc = 1
            elif after['max_vx_mm'] > 5 or after['max_vy_mm'] > 5 or \
                    after['max_vz_mrad'] > 5:
                print_error(f"  ROGUE MOTION — vx/vy/vz spiked from stale data "
                            f"after {label}")
                rc = 1
            else:
                print_success("  No rogue motion, stream stable.")
            print()

        # --- 3. Final stability check ---
        print(f'{Color.CYAN}Step 3: Final 2 s stream check{Color.RESET}')
        final = measure_baseline(proto, 2.0)
        print(f'  REPORT_SPEED final: {final["speed_hz"]:.1f} Hz '
              f'(baseline {base["speed_hz"]:.1f})')
        if abs(final['speed_hz'] - base['speed_hz']) > 5:
            print_warning("  Final rate differs from baseline by > 5 Hz")
        else:
            print_success("  Stream rate consistent end-to-end.")

        # --- 4. Summary ---
        print()
        print('=' * 60)
        print('SUMMARY')
        print('=' * 60)
        for label, r in rates:
            verdict = ("OK" if r['speed_hz'] >= 0.6 * base['speed_hz']
                       and r['max_vx_mm'] < 5
                       and r['max_vy_mm'] < 5
                       and r['max_vz_mrad'] < 5 else "FAIL")
            color = Color.GREEN if verdict == "OK" else Color.RED
            print(f'  {label:<28} {color}{verdict}{Color.RESET}  '
                  f'speed={r["speed_hz"]:.1f}Hz  motion=({r["max_vx_mm"]},'
                  f'{r["max_vy_mm"]},{r["max_vz_mrad"]})')
        print('=' * 60)
        if rc == 0:
            print_success("DD-1 risk did not manifest in this trial — but the "
                          "code-walk concern remains. Defence still recommended.")
        else:
            print_error("DD-1 manifested as observable misbehaviour.")

    except KeyboardInterrupt:
        print("\nInterrupted.")
        rc = 130
    finally:
        proto.stop()
        time.sleep(0.2)
        proto.enable_auto_report(False)
        proto.disconnect()

    return rc


if __name__ == "__main__":
    sys.exit(main())
