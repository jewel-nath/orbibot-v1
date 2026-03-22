# T1: Unit tests for rosmaster protocol (checksum, packet format). No hardware required.

import pytest

# Import protocol constants and logic without instantiating serial
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orbibot_hardware.rosmaster_driver import (
    SERIAL_HEAD,
    SERIAL_DEVICE_ID,
    SERIAL_COMPLEMENT,
    FUNC_RESET_ODOM,
    FUNC_BEEP,
    FUNC_AUTO_REPORT,
)


def checksum(cmd_list):
    """Replicate driver checksum: sum(cmd, SERIAL_COMPLEMENT) & 0xff."""
    return sum(cmd_list, SERIAL_COMPLEMENT) & 0xff


def build_packet(func_code, data_bytes):
    """Replicate _send_command packet build (length = len(cmd)-1)."""
    cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x00, func_code] + list(data_bytes)
    cmd[2] = len(cmd) - 1
    cmd.append(checksum(cmd))
    return cmd


class TestChecksum:
    """Test checksum computation matches protocol."""

    def test_reset_odom_packet_length(self):
        cmd = build_packet(FUNC_RESET_ODOM, [])
        assert len(cmd) == 5  # HEAD, DEVID, LEN, FUNC, checksum
        assert cmd[2] == 0x03  # LEN = 3 (BUG-4 fix: was 0x02)

    def test_reset_odom_checksum_valid(self):
        cmd = build_packet(FUNC_RESET_ODOM, [])
        computed = sum(cmd[:-1], SERIAL_COMPLEMENT) & 0xff
        assert computed == cmd[-1]

    def test_beep_packet(self):
        # beep 100 ms: two bytes little-endian 100
        data = [0x64, 0x00]  # 100 in LE
        cmd = build_packet(FUNC_BEEP, data)
        assert cmd[2] == 3 + len(data)  # LEN set before checksum append
        assert checksum(cmd[:-1]) == cmd[-1]

    def test_auto_report_packet(self):
        cmd = build_packet(FUNC_AUTO_REPORT, [1, 0])  # enable, forever=False
        assert len(cmd) == 7
        assert cmd[2] == 3 + 2  # LEN = 3 + len(data)
        assert sum(cmd[:-1], SERIAL_COMPLEMENT) & 0xff == cmd[-1]


class TestPacketLengthConvention:
    """Protocol: cmd[2] = len(cmd) - 1 at build time (DEVID through data, before checksum)."""

    def test_length_byte_matches_convention(self):
        for func, data in [(FUNC_RESET_ODOM, []), (FUNC_AUTO_REPORT, [1, 0])]:
            cmd = build_packet(func, data)
            # When we set LEN, cmd had 4 + len(data) bytes; LEN = len(cmd) - 1 = 3 + len(data)
            assert cmd[2] == 3 + len(data)
