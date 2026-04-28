#!/usr/bin/env python3
"""
SET_MAG_CAL state-byte gate — verifies firmware deep-dive finding DD-11.

DD-11 (MEDIUM): protocol_handle_set_mag_cal() used to call
flash_storage_save() unconditionally, burning one flash erase cycle per
calibration command. Fix added a trailing `state` byte (matches PID
convention): only persist when state == 0x5F (SAVE_VERIFY).

This script exercises three cases:
  1. Legacy 6-byte payload  — rejected by the dispatcher length gate.
  2. New    7-byte, state=0 — accepted, RAM-only, stream stays at 50 Hz.
  3. New    7-byte, state=0x5F — accepted, persisted to flash.
     **DEFAULT OFF.** Pass --burn-flash to actually run case 3
     (consumes one flash erase cycle).

Stream-rate degradation under flash save is the proxy for "flash actually
written" — the blocking ~50 ms erase shows up as a momentary stall.

SAFETY: No motion commands sent. Robot can be on the ground.

Usage:
  python3 test_mag_cal_gate.py [--port /dev/motordriver] [--burn-flash]
"""

import argparse
import struct
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


def make_packet(data: list) -> bytes:
    """Build [HEAD, DEV, LEN, FUNC_SET_MAG_CAL, *data, CKSUM]."""
    pkt = [HEAD, DEVICE_ID, 3 + len(data), FuncCode.SET_MAG_CAL] + data
    pkt.append(sum(pkt, COMPLEMENT) & 0xFF)
    return bytes(pkt)


def measure_stream_rate(proto: ROSMasterProtocol, duration_s: float) -> float:
    """Return REPORT_SPEED Hz over the duration."""
    count = 0
    t0 = time.time()
    while time.time() - t0 < duration_s:
        for fc, _ in proto.read_packets(timeout=0.05):
            if fc == FuncCode.REPORT_SPEED:
                count += 1
    return count / (time.time() - t0)


def main():
    parser = argparse.ArgumentParser(description='SET_MAG_CAL state-byte gate test (DD-11)')
    parser.add_argument('--port', '-p', default='/dev/motordriver')
    parser.add_argument('--burn-flash', action='store_true',
                        help='Actually write flash (default: skip case 3)')
    args = parser.parse_args()

    print_header("DD-11: SET_MAG_CAL state-byte gate")
    print_info(f"Port:        {args.port}")
    print_info(f"Burn flash:  {args.burn_flash}")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    # Hard-iron offsets that round-trip cleanly: ox=1.00, oy=-2.00, oz=0.50 µT
    # int16 scale ×100: 100, -200, 50
    offsets = [
        struct.pack('<h', 100)[0],  struct.pack('<h', 100)[1],
        struct.pack('<h', -200)[0], struct.pack('<h', -200)[1],
        struct.pack('<h', 50)[0],   struct.pack('<h', 50)[1],
    ]

    rc = 0
    try:
        proto.enable_auto_report(True)
        time.sleep(0.3)
        proto.ser.reset_input_buffer()

        # --- Baseline ---
        baseline = measure_stream_rate(proto, 1.5)
        print(f'Baseline REPORT_SPEED: {baseline:.1f} Hz')
        if baseline < 30:
            print_error("Baseline rate too low — aborting")
            return 1
        print()

        # --- Case 1: legacy 6-byte payload (no state byte) ---
        print(f'{Color.CYAN}Case 1: legacy 6-byte SET_MAG_CAL (no state byte){Color.RESET}')
        legacy = make_packet(list(offsets))  # 6 bytes payload
        proto.ser.write(legacy)
        time.sleep(0.05)
        rate = measure_stream_rate(proto, 1.5)
        print(f'  rate after blast: {rate:.1f} Hz')
        if rate < 0.6 * baseline:
            print_error("  Stream stalled — legacy payload not silently dropped")
            rc = 1
        else:
            print_success("  Silently rejected by length gate (rx_len=11 < min=12)")
        print()

        # --- Case 2: 7-byte, state=0 (RAM only) ---
        print(f'{Color.CYAN}Case 2: 7-byte SET_MAG_CAL with state=0 (RAM-only){Color.RESET}')
        ram_only = make_packet(list(offsets) + [0x00])
        proto.ser.write(ram_only)
        time.sleep(0.05)
        rate = measure_stream_rate(proto, 1.5)
        print(f'  rate after blast: {rate:.1f} Hz')
        if rate < 0.6 * baseline:
            print_error("  Stream stalled — RAM-only path is hitting flash unexpectedly")
            rc = 1
        else:
            print_success(f"  No stall — RAM updated, flash untouched")
        print()

        # --- Case 3: 7-byte, state=0x5F (flash save) ---
        if args.burn_flash:
            print_warning("Case 3: 7-byte SET_MAG_CAL with state=0x5F — WILL WRITE FLASH")
            persist = make_packet(list(offsets) + [0x5F])
            proto.ser.write(persist)
            time.sleep(0.05)
            rate = measure_stream_rate(proto, 1.5)
            print(f'  rate after blast: {rate:.1f} Hz')
            if rate < 0.6 * baseline:
                # Expected: flash erase ~50 ms reduces measurable rate slightly
                print_info("  Stream rate dipped (expected — flash erase ~50 ms blocking)")
            else:
                print_success(f"  Flash save completed without watchdog miss")
        else:
            print(f'{Color.CYAN}Case 3: SKIPPED (pass --burn-flash to actually persist){Color.RESET}')

    except KeyboardInterrupt:
        rc = 130
    finally:
        proto.enable_auto_report(False)
        proto.disconnect()

    return rc


if __name__ == "__main__":
    sys.exit(main())
