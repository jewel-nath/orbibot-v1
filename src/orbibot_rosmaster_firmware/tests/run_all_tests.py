#!/usr/bin/env python3
"""
Comprehensive Test Runner for OrbiBot Firmware

Runs all firmware tests in sequence with summary.
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode, PacketMonitor,
    print_header, print_info, print_success, print_error, print_warning, Color
)

# Minimum packets expected in 2 seconds — firmware sends 5 types at 20Hz = 200 total.
# Use 40 as a lenient floor (20%) to allow for startup latency.
MIN_EXPECTED_PACKETS = 40


def test_connection(proto: ROSMasterProtocol) -> bool:
    """Test basic serial connection."""
    print(f"\n{Color.CYAN}[1/6] Connection Test{Color.RESET}")

    if not proto.connect():
        print_error("Failed to connect")
        return False

    print_success(f"Connected to {proto.port}")
    return True


def test_auto_report(proto: ROSMasterProtocol) -> bool:
    """Test auto-report functionality."""
    print(f"\n{Color.CYAN}[2/6] Auto-Report Test{Color.RESET}")

    proto.enable_auto_report(True)
    time.sleep(0.5)

    monitor = PacketMonitor(proto)
    monitor.start()

    # Collect for 2 seconds
    while monitor.elapsed < 2.0:
        monitor.process(timeout=0.1)

    proto.enable_auto_report(False)

    if monitor.total_packets > MIN_EXPECTED_PACKETS:
        print_success(f"Received {monitor.total_packets} packets in {monitor.elapsed:.1f}s")
        return True
    else:
        print_error(f"Only received {monitor.total_packets} packets (expected >{MIN_EXPECTED_PACKETS})")
        return False


def test_encoders(proto: ROSMasterProtocol) -> bool:
    """Test encoder data reception."""
    print(f"\n{Color.CYAN}[3/6] Encoder Test{Color.RESET}")

    proto.enable_auto_report(True)
    time.sleep(0.3)

    encoder_count = 0
    start = time.time()

    while time.time() - start < 2.0:
        packets = proto.read_packets(timeout=0.1)
        for func_code, payload in packets:
            if func_code == FuncCode.REPORT_ENCODER:
                data = proto.parse_encoder(payload)
                if data:
                    encoder_count += 1
                    if encoder_count == 1:
                        print_info(f"Encoder values: M1={data.m1}, M2={data.m2}, M3={data.m3}, M4={data.m4}")

    proto.enable_auto_report(False)

    if encoder_count > 0:
        print_success(f"Received {encoder_count} encoder packets")
        return True
    else:
        print_error("No encoder data received")
        return False


def test_imu(proto: ROSMasterProtocol) -> bool:
    """Test IMU data reception."""
    print(f"\n{Color.CYAN}[4/6] IMU Test{Color.RESET}")

    proto.enable_auto_report(True)
    time.sleep(0.3)

    imu_raw_count = 0
    imu_att_count = 0
    start = time.time()

    while time.time() - start < 2.0:
        packets = proto.read_packets(timeout=0.1)
        for func_code, payload in packets:
            if func_code == FuncCode.REPORT_IMU_RAW:
                imu_raw_count += 1
            elif func_code == FuncCode.REPORT_IMU_ATTITUDE:
                data = proto.parse_imu_attitude(payload)
                if data and imu_att_count == 0:
                    print_info(f"Attitude: Roll={data.roll:.1f}, Pitch={data.pitch:.1f}, Yaw={data.yaw:.1f}")
                imu_att_count += 1

    proto.enable_auto_report(False)

    if imu_raw_count > 0 and imu_att_count > 0:
        print_success(f"Received {imu_raw_count} raw + {imu_att_count} attitude packets")
        return True
    else:
        print_error(f"IMU data incomplete (raw={imu_raw_count}, att={imu_att_count})")
        return False


def test_battery(proto: ROSMasterProtocol) -> bool:
    """Test battery voltage reading."""
    print(f"\n{Color.CYAN}[5/6] Battery Test{Color.RESET}")

    proto.enable_auto_report(True)
    time.sleep(0.3)

    voltage = None
    start = time.time()

    while time.time() - start < 2.0:
        packets = proto.read_packets(timeout=0.1)
        for func_code, payload in packets:
            if func_code == FuncCode.REPORT_SPEED:
                data = proto.parse_speed(payload)
                if data:
                    voltage = data.battery_v
                    break
        if voltage:
            break

    proto.enable_auto_report(False)

    if voltage and voltage > 5.0:
        if voltage >= 12.8:  # 4S LiFePO4 nominal
            print_success(f"Battery voltage: {voltage:.1f}V (Good)")
        elif voltage >= 11.0:  # low warning threshold
            print_warning(f"Battery voltage: {voltage:.1f}V (Low)")
        else:
            print_error(f"Battery voltage: {voltage:.1f}V (Critical)")
        return True
    else:
        print_error("Invalid battery reading")
        return False


def test_beep(proto: ROSMasterProtocol) -> bool:
    """Test buzzer."""
    print(f"\n{Color.CYAN}[6/6] Beep Test{Color.RESET}")

    print_info("Sending beep command...")
    proto.beep(100)
    time.sleep(0.2)

    print_success("Beep command sent (listen for sound)")
    return True  # Can't verify audio programmatically


def main():
    parser = argparse.ArgumentParser(description='Run all firmware tests')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    parser.add_argument('--skip-beep', action='store_true', help='Skip beep test')
    args = parser.parse_args()

    print_header("ORBIBOT FIRMWARE TEST SUITE")
    print_info(f"Port: {args.port}")
    print()

    proto = ROSMasterProtocol(args.port)
    results = {}

    try:
        # Run tests
        results['Connection'] = test_connection(proto)

        if results['Connection']:
            results['Auto-Report'] = test_auto_report(proto)
            results['Encoders'] = test_encoders(proto)
            results['IMU'] = test_imu(proto)
            results['Battery'] = test_battery(proto)

            if not args.skip_beep:
                results['Beep'] = test_beep(proto)

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.disconnect()

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for r in results.values() if r)
    failed = sum(1 for r in results.values() if not r)

    for name, result in results.items():
        if result:
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print()
    print(f"Results: {Color.GREEN}{passed} passed{Color.RESET}, {Color.RED}{failed} failed{Color.RESET}")

    if failed == 0:
        print()
        print_success("All tests passed! Firmware is working correctly.")
        return 0
    else:
        print()
        print_error("Some tests failed. Check firmware and connections.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
