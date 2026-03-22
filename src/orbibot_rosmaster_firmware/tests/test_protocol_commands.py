#!/usr/bin/env python3
"""
Protocol Command Unit Tests for OrbiBot Firmware

Offline (no hardware required) — verifies that rosmaster_protocol.py builds
packets with correct function codes, lengths, and checksums.

Run: python3 test_protocol_commands.py
"""

import struct
import sys
import unittest

# Protocol constants (duplicated here to avoid serial import dependency)
HEAD = 0xFF
DEVICE_ID = 0xFC
COMPLEMENT = 257 - DEVICE_ID


def build_packet(func_code: int, data: list) -> list:
    """Build a protocol packet: [HEAD][DEVID][LEN][FUNC][data...][checksum]."""
    packet = [HEAD, DEVICE_ID, 0x00, func_code] + data
    packet[2] = len(packet) - 1  # LEN = bytes from DEVID through last data byte
    checksum = sum(packet, COMPLEMENT) & 0xFF
    packet.append(checksum)
    return packet


def checksum_valid(packet: list) -> bool:
    """Verify checksum of a built packet."""
    expected = sum(packet[:-1], COMPLEMENT) & 0xFF
    return expected == packet[-1]


class TestPacketStructure(unittest.TestCase):
    """Verify packet header structure and length convention."""

    def test_head_byte(self):
        pkt = build_packet(0x01, [])
        self.assertEqual(pkt[0], 0xFF)

    def test_device_id_byte(self):
        pkt = build_packet(0x01, [])
        self.assertEqual(pkt[1], 0xFC)

    def test_length_no_data(self):
        # LEN = len(packet_before_checksum) - 1 = 3 (DEVID, LEN, FUNC)
        pkt = build_packet(0x01, [])
        self.assertEqual(pkt[2], 3)

    def test_length_with_data(self):
        data = [0x01, 0x02, 0x03]
        pkt = build_packet(0x01, data)
        self.assertEqual(pkt[2], 3 + len(data))

    def test_checksum_no_data(self):
        pkt = build_packet(0x01, [])
        self.assertTrue(checksum_valid(pkt))

    def test_checksum_with_data(self):
        pkt = build_packet(0x12, [0x07, 0xE8, 0x03, 0x00, 0x00, 0x00, 0x00])
        self.assertTrue(checksum_valid(pkt))


class TestAutoReportPacket(unittest.TestCase):
    """FUNC_AUTO_REPORT = 0x01: enable/disable auto-report."""

    FUNC = 0x01

    def test_enable_packet(self):
        pkt = build_packet(self.FUNC, [0x01, 0x00])
        self.assertEqual(pkt[3], self.FUNC)
        self.assertEqual(pkt[4], 0x01)   # enable
        self.assertEqual(pkt[5], 0x00)   # not permanent
        self.assertEqual(len(pkt), 7)
        self.assertTrue(checksum_valid(pkt))

    def test_disable_packet(self):
        pkt = build_packet(self.FUNC, [0x00, 0x00])
        self.assertEqual(pkt[4], 0x00)
        self.assertTrue(checksum_valid(pkt))

    def test_permanent_enable(self):
        pkt = build_packet(self.FUNC, [0x01, 0x5F])
        self.assertEqual(pkt[5], 0x5F)   # forever flag
        self.assertTrue(checksum_valid(pkt))


class TestBeepPacket(unittest.TestCase):
    """FUNC_BEEP = 0x02: buzzer control."""

    FUNC = 0x02

    def test_beep_100ms(self):
        duration_ms = 100
        data = list(struct.pack('<H', duration_ms))
        pkt = build_packet(self.FUNC, data)
        self.assertEqual(pkt[3], self.FUNC)
        self.assertEqual(pkt[4], 0x64)   # 100 low byte
        self.assertEqual(pkt[5], 0x00)   # 100 high byte
        self.assertTrue(checksum_valid(pkt))

    def test_beep_off(self):
        pkt = build_packet(self.FUNC, [0x00, 0x00])
        self.assertTrue(checksum_valid(pkt))

    def test_beep_continuous(self):
        pkt = build_packet(self.FUNC, list(struct.pack('<H', 1)))
        self.assertEqual(pkt[4], 0x01)
        self.assertTrue(checksum_valid(pkt))


class TestResetPackets(unittest.TestCase):
    """FUNC_RESET_ENCODERS = 0x08, FUNC_RESET_ODOM = 0x09: no data payload."""

    def test_reset_encoders_packet(self):
        pkt = build_packet(0x08, [])
        self.assertEqual(pkt[3], 0x08)
        self.assertEqual(len(pkt), 5)    # HEAD DEVID LEN FUNC checksum
        self.assertEqual(pkt[2], 3)      # LEN = 3
        self.assertTrue(checksum_valid(pkt))

    def test_reset_odom_packet(self):
        pkt = build_packet(0x09, [])
        self.assertEqual(pkt[3], 0x09)
        self.assertEqual(len(pkt), 5)
        self.assertEqual(pkt[2], 3)
        self.assertTrue(checksum_valid(pkt))


class TestMotionPacket(unittest.TestCase):
    """FUNC_MOTION = 0x12: car_type + vx + vy + vz (int16 LE each)."""

    FUNC = 0x12
    CAR_TYPE = 0x07  # CARTYPE_ORBIBOT

    def _make_motion(self, vx_m, vy_m, vz_rad):
        vx_mm = int(vx_m * 1000)
        vy_mm = int(vy_m * 1000)
        vz_mrad = int(vz_rad * 1000)
        data = [self.CAR_TYPE]
        data.extend(struct.pack('<h', vx_mm))
        data.extend(struct.pack('<h', vy_mm))
        data.extend(struct.pack('<h', vz_mrad))
        return build_packet(self.FUNC, data)

    def test_stop_packet(self):
        pkt = self._make_motion(0, 0, 0)
        self.assertEqual(pkt[3], self.FUNC)
        self.assertEqual(pkt[4], self.CAR_TYPE)
        # vx bytes (5,6), vy bytes (7,8), vz bytes (9,10) should all be zero
        self.assertEqual(pkt[5:11], [0, 0, 0, 0, 0, 0])
        self.assertTrue(checksum_valid(pkt))

    def test_forward_motion(self):
        pkt = self._make_motion(0.3, 0, 0)  # 300 mm/s forward
        self.assertEqual(pkt[3], self.FUNC)
        vx = struct.unpack('<h', bytes(pkt[5:7]))[0]
        self.assertEqual(vx, 300)
        vy = struct.unpack('<h', bytes(pkt[7:9]))[0]
        self.assertEqual(vy, 0)
        self.assertTrue(checksum_valid(pkt))

    def test_lateral_motion(self):
        pkt = self._make_motion(0, 0.2, 0)  # 200 mm/s lateral
        vy = struct.unpack('<h', bytes(pkt[7:9]))[0]
        self.assertEqual(vy, 200)
        self.assertTrue(checksum_valid(pkt))

    def test_rotation(self):
        pkt = self._make_motion(0, 0, 1.0)  # 1 rad/s rotation → 1000 mrad/s
        vz = struct.unpack('<h', bytes(pkt[9:11]))[0]
        self.assertEqual(vz, 1000)
        self.assertTrue(checksum_valid(pkt))

    def test_packet_length(self):
        # HEAD DEVID LEN FUNC CAR_TYPE(1) VX[2] VY[2] VZ[2] CHECKSUM
        # data = 7 bytes; packet before checksum = 11 bytes; LEN = 10
        pkt = self._make_motion(0, 0, 0)
        self.assertEqual(len(pkt), 12)
        self.assertEqual(pkt[2], 10)
        self.assertTrue(checksum_valid(pkt))


class TestMotorPIDPacket(unittest.TestCase):
    """FUNC_SET_MOTOR_PID = 0x13: kp, ki, kd (int16 LE ×1000), state byte."""

    FUNC = 0x13

    def _make_pid(self, kp, ki, kd, forever=False):
        state = 0x5F if forever else 0x00
        kp_b = list(struct.pack('<h', int(kp * 1000)))
        ki_b = list(struct.pack('<h', int(ki * 1000)))
        kd_b = list(struct.pack('<h', int(kd * 1000)))
        return build_packet(self.FUNC, kp_b + ki_b + kd_b + [state])

    def test_pid_packet_length(self):
        pkt = self._make_pid(0.8, 0.06, 0.5)
        # HEAD DEVID LEN FUNC kp[2] ki[2] kd[2] state(1) checksum = 12 bytes
        # data = 7 bytes; LEN = 10
        self.assertEqual(len(pkt), 12)

    def test_pid_values_encoded(self):
        pkt = self._make_pid(1.0, 0.1, 0.5)
        kp = struct.unpack('<h', bytes(pkt[4:6]))[0]
        ki = struct.unpack('<h', bytes(pkt[6:8]))[0]
        kd = struct.unpack('<h', bytes(pkt[8:10]))[0]
        self.assertEqual(kp, 1000)
        self.assertEqual(ki, 100)
        self.assertEqual(kd, 500)

    def test_pid_temporary(self):
        pkt = self._make_pid(0.8, 0.06, 0.5, forever=False)
        self.assertEqual(pkt[10], 0x00)
        self.assertTrue(checksum_valid(pkt))

    def test_pid_permanent(self):
        pkt = self._make_pid(0.8, 0.06, 0.5, forever=True)
        self.assertEqual(pkt[10], 0x5F)
        self.assertTrue(checksum_valid(pkt))

    def test_length_byte_dynamic(self):
        # LEN must be set dynamically (not hardcoded 0x0A) — key fix from HW-BUG-1
        pkt = self._make_pid(0.8, 0.06, 0.5)
        expected_len = len(pkt) - 2  # excludes HEAD and DEVID, includes checksum
        self.assertEqual(pkt[2], expected_len)


class TestMagCalibrationPacket(unittest.TestCase):
    """FUNC_SET_MAG_CAL = 0x16: ox, oy, oz as int16 LE (×100 scaling, units µT)."""

    FUNC = 0x16

    def _make_mag_cal(self, ox, oy, oz):
        ox_b = list(struct.pack('<h', int(ox * 100)))
        oy_b = list(struct.pack('<h', int(oy * 100)))
        oz_b = list(struct.pack('<h', int(oz * 100)))
        return build_packet(self.FUNC, ox_b + oy_b + oz_b)

    def test_zero_offsets(self):
        pkt = self._make_mag_cal(0.0, 0.0, 0.0)
        self.assertEqual(pkt[3], self.FUNC)
        self.assertEqual(pkt[4:10], [0, 0, 0, 0, 0, 0])
        self.assertTrue(checksum_valid(pkt))

    def test_offsets_encoded(self):
        # 5.2 µT × 100 = 520 = 0x0208 (LE: 0x08, 0x02)
        pkt = self._make_mag_cal(5.2, -3.1, 1.0)
        ox = struct.unpack('<h', bytes(pkt[4:6]))[0]
        oy = struct.unpack('<h', bytes(pkt[6:8]))[0]
        oz = struct.unpack('<h', bytes(pkt[8:10]))[0]
        self.assertEqual(ox, 520)
        self.assertEqual(oy, -310)
        self.assertEqual(oz, 100)

    def test_packet_length(self):
        pkt = self._make_mag_cal(1.0, 2.0, 3.0)
        # HEAD DEVID LEN FUNC ox[2] oy[2] oz[2] checksum = 11 bytes
        # data = 6 bytes; LEN = 9
        self.assertEqual(len(pkt), 11)

    def test_checksum_valid(self):
        pkt = self._make_mag_cal(5.2, -3.1, 1.0)
        self.assertTrue(checksum_valid(pkt))

    def test_max_positive_offset(self):
        # 327.67 µT × 100 = 32767 = INT16_MAX
        pkt = self._make_mag_cal(327.67, 0.0, 0.0)
        ox = struct.unpack('<h', bytes(pkt[4:6]))[0]
        self.assertEqual(ox, 32767)
        self.assertTrue(checksum_valid(pkt))

    def test_max_negative_offset(self):
        pkt = self._make_mag_cal(-327.67, 0.0, 0.0)
        ox = struct.unpack('<h', bytes(pkt[4:6]))[0]
        self.assertEqual(ox, -32767)
        self.assertTrue(checksum_valid(pkt))


class TestFuncCodes(unittest.TestCase):
    """Verify function codes match firmware protocol.h."""

    def test_func_auto_report(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.AUTO_REPORT, 0x01)

    def test_func_beep(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.BEEP, 0x02)

    def test_func_reset_encoders(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.RESET_ENCODERS, 0x08)

    def test_func_report_speed(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.REPORT_SPEED, 0x0A)

    def test_func_report_imu_attitude(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.REPORT_IMU_ATTITUDE, 0x0C)

    def test_func_report_encoder(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.REPORT_ENCODER, 0x0D)

    def test_func_report_imu_raw(self):
        from rosmaster_protocol import FuncCode
        # Must be 0x0E (FUNC_REPORT_ICM_RAW in firmware protocol.h)
        self.assertEqual(FuncCode.REPORT_IMU_RAW, 0x0E)

    def test_func_report_odom(self):
        from rosmaster_protocol import FuncCode
        # Must be 0x15 (FUNC_REPORT_ODOM in firmware protocol.h)
        self.assertEqual(FuncCode.REPORT_ODOM, 0x15)

    def test_func_set_motor_pid(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.SET_MOTOR_PID, 0x13)

    def test_func_set_mag_cal(self):
        from rosmaster_protocol import FuncCode
        self.assertEqual(FuncCode.SET_MAG_CAL, 0x16)


class TestIMURawParsing(unittest.TestCase):
    """Verify parse_imu_raw handles 18-byte payload (gyro+accel+mag)."""

    def _make_raw_payload(self, gyro, accel, mag):
        """Build 18-byte IMU raw payload from (gx,gy,gz), (ax,ay,az), (mx,my,mz)."""
        return struct.pack('<9h', *gyro, *accel, *mag)

    def test_rejects_short_payload(self):
        from rosmaster_protocol import ROSMasterProtocol
        proto = ROSMasterProtocol.__new__(ROSMasterProtocol)
        result = proto.parse_imu_raw(b'\x00' * 17)  # 17 bytes — too short
        self.assertIsNone(result)

    def test_parses_18_bytes(self):
        from rosmaster_protocol import ROSMasterProtocol
        proto = ROSMasterProtocol.__new__(ROSMasterProtocol)
        gyro = (100, -200, 300)
        accel = (0, 0, 16000)
        mag = (50, -30, 10)
        payload = self._make_raw_payload(gyro, accel, mag)
        result = proto.parse_imu_raw(payload)
        self.assertIsNotNone(result)
        self.assertEqual(result.gyro_x, 100)
        self.assertEqual(result.gyro_y, -200)
        self.assertEqual(result.gyro_z, 300)
        self.assertEqual(result.accel_x, 0)
        self.assertEqual(result.accel_y, 0)
        self.assertEqual(result.accel_z, 16000)
        self.assertEqual(result.mag_x, 50)
        self.assertEqual(result.mag_y, -30)
        self.assertEqual(result.mag_z, 10)

    def test_accepts_exactly_18_bytes(self):
        from rosmaster_protocol import ROSMasterProtocol
        proto = ROSMasterProtocol.__new__(ROSMasterProtocol)
        result = proto.parse_imu_raw(b'\x00' * 18)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
