#!/usr/bin/env python3
"""
Firmware Version Test Script for OrbiBot Firmware

Requests and displays firmware version information.
"""

import sys
import time
import argparse
from rosmaster_protocol import (
    ROSMasterProtocol, FuncCode,
    print_header, print_info, print_success, print_error, Color
)


def main():
    parser = argparse.ArgumentParser(description='Get firmware version')
    parser.add_argument('--port', '-p', default='/dev/motordriver', help='Serial port')
    args = parser.parse_args()

    print_header("FIRMWARE VERSION TEST")
    print_info(f"Port: {args.port}")
    print()

    proto = ROSMasterProtocol(args.port)
    if not proto.connect():
        print_error(f"Failed to connect to {args.port}")
        return 1

    try:
        # Request firmware version
        print("Requesting firmware version...")
        proto.send(FuncCode.VERSION)
        time.sleep(0.2)

        # Read response
        packets = proto.read_packets(timeout=1.0)
        version_found = False

        for func_code, payload in packets:
            if func_code == FuncCode.VERSION:
                version_found = True
                if len(payload) >= 3:
                    major = payload[0]
                    minor = payload[1]
                    patch = payload[2]
                    print_success(f"Firmware version: {major}.{minor}.{patch}")
                else:
                    print_info(f"Version payload: {payload.hex()}")

        if not version_found:
            print_error("No version response received")
            print_info("Firmware may not support version query")

    except KeyboardInterrupt:
        print("\n\nTest interrupted.")

    finally:
        proto.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
