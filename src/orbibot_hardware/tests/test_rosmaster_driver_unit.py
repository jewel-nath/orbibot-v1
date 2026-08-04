# T3: Unit tests for Rosmaster driver — protocol parsing and command building.
# No hardware required (mocks serial.Serial).

import math
import struct
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# test_hardware_node_unit.py installs a MagicMock at
# sys.modules['orbibot_hardware.rosmaster_driver'], deliberately, to push
# hardware_node.py down its `except ImportError` branch — and never restores it.
# pytest imports every test module during collection, alphabetically, so that
# stub is already in place by the time this file is imported and every assertion
# here would run against a MagicMock instead of the real driver.
#
# The symptom is misleading: each file passes on its own, and 34 tests fail only
# when the directory is run as a whole. Evict the stub so this module always gets
# the real thing, whatever ran before it.
sys.modules.pop('orbibot_hardware.rosmaster_driver', None)

from orbibot_hardware.rosmaster_driver import (
    Rosmaster,
    SERIAL_HEAD, SERIAL_DEVICE_ID, SERIAL_COMPLEMENT,
    FUNC_REPORT_SPEED, FUNC_REPORT_ICM_RAW, FUNC_REPORT_IMU_ATT,
    FUNC_REPORT_ENCODER, FUNC_REPORT_ODOM,
    FUNC_SET_MOTOR_PID, FUNC_SET_YAW_PID,
    FUNC_BEEP, FUNC_MOTION, FUNC_AUTO_REPORT,
    FUNC_RESET_ENCODERS, FUNC_RESET_ODOM,
    ICM20948_GYRO_RATIO, ICM20948_ACCEL_RATIO,
    CARTYPE_ORBIBOT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rosmaster():
    """Return a Rosmaster with a mocked serial port (using CARTYPE_ORBIBOT as hardware_node does)."""
    with patch('serial.Serial') as mock_serial_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_serial_cls.return_value = mock_ser
        driver = Rosmaster(car_type=CARTYPE_ORBIBOT, com='/dev/null', debug=False)
        driver.ser = mock_ser
    return driver


def _checksum(cmd_list):
    return sum(cmd_list, SERIAL_COMPLEMENT) & 0xFF


def _build_rx_packet(func_code: int, data: list) -> bytes:
    """Build a packet as the firmware would send it (DEVID = SERIAL_DEVICE_ID - 1)."""
    devid_reply = SERIAL_DEVICE_ID - 1  # 0xFB
    payload = [func_code] + data
    # LEN = number of bytes from func_code through checksum (inclusive)
    check = (len(payload) + sum(data)) & 0xFF
    pkt = bytes([SERIAL_HEAD, devid_reply, len(payload) + 1] + payload + [check])
    return pkt


# ---------------------------------------------------------------------------
# Protocol parsing — FUNC_REPORT_SPEED
# ---------------------------------------------------------------------------

class TestParseSpeed:
    def test_parses_velocity_and_battery(self):
        driver = _make_rosmaster()
        # vx=300 mm/s, vy=-100 mm/s, vz=500 mrad/s, battery=128 (→ 12.8V)
        data = list(struct.pack('<h', 300))   # vx
        data += list(struct.pack('<h', -100))  # vy
        data += list(struct.pack('<h', 500))   # vz
        data += [128]                          # battery byte
        driver._parse_data(FUNC_REPORT_SPEED, data)

        vx, vy, vz = driver.get_motion_data()
        assert pytest.approx(vx, abs=1e-4) == 0.3
        assert pytest.approx(vy, abs=1e-4) == -0.1
        assert pytest.approx(vz, abs=1e-4) == 0.5
        assert pytest.approx(driver.get_battery_voltage(), abs=1e-4) == 12.8

    def test_rejects_short_payload(self):
        driver = _make_rosmaster()
        driver._parse_data(FUNC_REPORT_SPEED, [0] * 6)  # 6 bytes — too short
        vx, vy, vz = driver.get_motion_data()
        assert vx == 0.0  # unchanged default

    def test_battery_voltage_scale(self):
        driver = _make_rosmaster()
        data = [0, 0, 0, 0, 0, 0, 146]  # battery byte = 146 → 14.6V
        driver._parse_data(FUNC_REPORT_SPEED, data)
        assert pytest.approx(driver.get_battery_voltage(), abs=1e-4) == 14.6


# ---------------------------------------------------------------------------
# Protocol parsing — FUNC_REPORT_ICM_RAW (12-byte payload, no mag)
# ---------------------------------------------------------------------------

class TestParseICMRaw:
    def test_parses_gyro_accel(self):
        driver = _make_rosmaster()
        # Construct 12-byte payload: gyro(6) + accel(6)
        gyro = (1000, -500, 250)   # mrad/s
        accel = (0, 0, 9810)       # mm/s²
        data = list(struct.pack('<6h', *gyro, *accel))
        driver._parse_data(FUNC_REPORT_ICM_RAW, data)

        gx, gy, gz = driver.get_gyroscope_data()
        assert pytest.approx(gx, abs=1e-6) == 1000 * ICM20948_GYRO_RATIO
        assert pytest.approx(gy, abs=1e-6) == -500 * ICM20948_GYRO_RATIO
        assert pytest.approx(gz, abs=1e-6) == 250 * ICM20948_GYRO_RATIO

        ax, ay, az = driver.get_accelerometer_data()
        assert pytest.approx(az, abs=1e-6) == 9810 * ICM20948_ACCEL_RATIO

    def test_rejects_short_payload(self):
        driver = _make_rosmaster()
        driver._parse_data(FUNC_REPORT_ICM_RAW, [0] * 11)  # too short — rejected
        gx, gy, gz = driver.get_gyroscope_data()
        assert gx == 0.0

    def test_accepts_12_byte_payload(self):
        driver = _make_rosmaster()
        driver._parse_data(FUNC_REPORT_ICM_RAW, [0] * 12)
        # Should not raise


# ---------------------------------------------------------------------------
# Protocol parsing — FUNC_REPORT_IMU_ATT
# ---------------------------------------------------------------------------

class TestParseIMUAttitude:
    def test_parses_roll_pitch_yaw(self):
        driver = _make_rosmaster()
        # roll=0.1 rad → encoded as 1000, pitch=-0.2 rad → -2000, yaw=1.5708 rad → ~15708
        roll_enc = int(0.1 * 10000)
        pitch_enc = int(-0.2 * 10000)
        yaw_enc = int(1.5708 * 10000)
        data = list(struct.pack('<3h', roll_enc, pitch_enc, yaw_enc))
        driver._parse_data(FUNC_REPORT_IMU_ATT, data)

        roll_r, pitch_r, yaw_r = driver.get_imu_attitude_data(to_angle=False)
        assert pytest.approx(roll_r, abs=1e-4) == 0.1
        assert pytest.approx(pitch_r, abs=1e-4) == -0.2
        assert pytest.approx(yaw_r, abs=1e-4) == 1.5708

    def test_to_degrees_conversion(self):
        driver = _make_rosmaster()
        roll_enc = int(math.pi / 2 * 10000)  # 90 degrees
        data = list(struct.pack('<3h', roll_enc, 0, 0))
        driver._parse_data(FUNC_REPORT_IMU_ATT, data)

        roll_deg, _, _ = driver.get_imu_attitude_data(to_angle=True)
        assert pytest.approx(roll_deg, abs=0.01) == 90.0

    def test_rejects_short_payload(self):
        driver = _make_rosmaster()
        driver._parse_data(FUNC_REPORT_IMU_ATT, [0] * 5)
        roll, _, _ = driver.get_imu_attitude_data(to_angle=False)
        assert roll == 0.0


# ---------------------------------------------------------------------------
# Protocol parsing — FUNC_REPORT_ENCODER
# ---------------------------------------------------------------------------

class TestParseEncoder:
    def test_parses_four_motors(self):
        driver = _make_rosmaster()
        counts = (1000, -500, 2000, -1500)
        data = list(struct.pack('<4i', *counts))
        driver._parse_data(FUNC_REPORT_ENCODER, data)

        m1, m2, m3, m4 = driver.get_motor_encoder()
        assert m1 == 1000
        assert m2 == -500
        assert m3 == 2000
        assert m4 == -1500

    def test_rejects_short_payload(self):
        driver = _make_rosmaster()
        driver._parse_data(FUNC_REPORT_ENCODER, [0] * 15)
        m1, m2, m3, m4 = driver.get_motor_encoder()
        assert m1 == 0  # unchanged

    def test_large_counts(self):
        driver = _make_rosmaster()
        counts = (2147483647, -2147483648, 0, 0)  # INT32 extremes
        data = list(struct.pack('<4i', *counts))
        driver._parse_data(FUNC_REPORT_ENCODER, data)
        m1, m2, _, _ = driver.get_motor_encoder()
        assert m1 == 2147483647
        assert m2 == -2147483648


# ---------------------------------------------------------------------------
# Protocol parsing — FUNC_REPORT_ODOM
# ---------------------------------------------------------------------------

class TestParseOdom:
    def test_parses_pose_and_velocity(self):
        driver = _make_rosmaster()
        # x=1500 mm, y=-300 mm, theta=1571 mrad (~90°),
        # vx=200 mm/s, vy=-100 mm/s, omega=314 mrad/s
        vals = (1500, -300, 1571, 200, -100, 314)
        data = list(struct.pack('<6i', *vals))
        driver._parse_data(FUNC_REPORT_ODOM, data)

        x, y, theta, vx, vy, omega = driver.get_firmware_odometry()
        assert pytest.approx(x, abs=1e-4) == 1.5
        assert pytest.approx(y, abs=1e-4) == -0.3
        assert pytest.approx(theta, abs=1e-4) == 1.571
        assert pytest.approx(vx, abs=1e-4) == 0.2
        assert pytest.approx(vy, abs=1e-4) == -0.1
        assert pytest.approx(omega, abs=1e-4) == 0.314

    def test_rejects_short_payload(self):
        driver = _make_rosmaster()
        driver._parse_data(FUNC_REPORT_ODOM, [0] * 23)  # 23 < 24
        x, y, theta, vx, vy, omega = driver.get_firmware_odometry()
        assert x == 0.0


# ---------------------------------------------------------------------------
# Command building — set_beep
# ---------------------------------------------------------------------------

class TestSetBeep:
    def test_raises_on_negative(self):
        driver = _make_rosmaster()
        with pytest.raises(ValueError, match='on_time'):
            driver.set_beep(-1)

    def test_sends_zero_off(self):
        driver = _make_rosmaster()
        driver.set_beep(0)
        written = driver.ser.write.call_args[0][0]
        assert written[3] == FUNC_BEEP
        assert written[4] == 0x00
        assert written[5] == 0x00

    def test_sends_100ms(self):
        driver = _make_rosmaster()
        driver.set_beep(100)
        written = driver.ser.write.call_args[0][0]
        assert written[3] == FUNC_BEEP
        val = struct.unpack('<H', bytes(written[4:6]))[0]
        assert val == 100


# ---------------------------------------------------------------------------
# Command building — set_pid_param
# ---------------------------------------------------------------------------

class TestSetPidParam:
    def _get_written(self, driver):
        return bytearray(driver.ser.write.call_args[0][0])

    def test_sends_correct_func_code(self):
        driver = _make_rosmaster()
        driver.set_pid_param(0.8, 0.06, 0.5)
        pkt = self._get_written(driver)
        assert pkt[3] == FUNC_SET_MOTOR_PID

    def test_length_byte_is_dynamic(self):
        """Regression test for HW-BUG-1: length byte must not be hardcoded 0x0A."""
        driver = _make_rosmaster()
        driver.set_pid_param(0.8, 0.06, 0.5)
        pkt = self._get_written(driver)
        expected_len = len(pkt) - 2  # excludes HEAD and DEVID
        assert pkt[2] == expected_len

    def test_pid_values_encoded(self):
        driver = _make_rosmaster()
        driver.set_pid_param(1.0, 0.1, 0.5)
        pkt = self._get_written(driver)
        kp = struct.unpack('<h', bytes(pkt[4:6]))[0]
        ki = struct.unpack('<h', bytes(pkt[6:8]))[0]
        kd = struct.unpack('<h', bytes(pkt[8:10]))[0]
        assert kp == 1000
        assert ki == 100
        assert kd == 500

    def test_temporary_state_byte(self):
        driver = _make_rosmaster()
        driver.set_pid_param(0.8, 0.06, 0.5, forever=False)
        pkt = self._get_written(driver)
        assert pkt[10] == 0x00

    def test_permanent_state_byte(self):
        driver = _make_rosmaster()
        driver.set_pid_param(0.8, 0.06, 0.5, forever=True)
        pkt = self._get_written(driver)
        assert pkt[10] == 0x5F

    def test_checksum_valid(self):
        driver = _make_rosmaster()
        driver.set_pid_param(0.8, 0.06, 0.5)
        pkt = list(self._get_written(driver))
        expected = _checksum(pkt[:-1])
        assert pkt[-1] == expected

    def test_rejects_out_of_range(self):
        """Out-of-range gains raise, and nothing reaches the wire.

        This test used to assert the value was "silently ignored". The driver
        raises ValueError instead, which is the better behaviour — a PID gain
        that vanishes without complaint is how a robot ends up mistuned with no
        evidence. The assertion was stale, not the driver.
        """
        driver = _make_rosmaster()
        with pytest.raises(ValueError):
            driver.set_pid_param(11.0, 0.0, 0.0)   # kp > 10
        driver.ser.write.assert_not_called()

    def test_rejects_negative(self):
        driver = _make_rosmaster()
        with pytest.raises(ValueError):
            driver.set_pid_param(-0.1, 0.0, 0.0)
        driver.ser.write.assert_not_called()


# ---------------------------------------------------------------------------
# Command building — set_yaw_pid_param
# ---------------------------------------------------------------------------

class TestSetYawPidParam:
    def _get_written(self, driver):
        return bytearray(driver.ser.write.call_args[0][0])

    def test_sends_correct_func_code(self):
        driver = _make_rosmaster()
        driver.set_yaw_pid_param(0.4, 0.0, 0.1)
        pkt = self._get_written(driver)
        assert pkt[3] == FUNC_SET_YAW_PID

    def test_length_byte_is_dynamic(self):
        """Regression test for HW-BUG-1: length byte must not be hardcoded 0x0A."""
        driver = _make_rosmaster()
        driver.set_yaw_pid_param(0.4, 0.0, 0.1)
        pkt = self._get_written(driver)
        expected_len = len(pkt) - 2
        assert pkt[2] == expected_len

    def test_checksum_valid(self):
        driver = _make_rosmaster()
        driver.set_yaw_pid_param(0.4, 0.0, 0.1)
        pkt = list(self._get_written(driver))
        expected = _checksum(pkt[:-1])
        assert pkt[-1] == expected


# ---------------------------------------------------------------------------
# Command building — set_car_motion
# ---------------------------------------------------------------------------

class TestSetCarMotion:
    def _get_written(self, driver):
        return bytearray(driver.ser.write.call_args[0][0])

    def test_stop_packet(self):
        driver = _make_rosmaster()
        driver.set_car_motion(0, 0, 0)
        pkt = self._get_written(driver)
        assert pkt[3] == FUNC_MOTION
        assert pkt[4] == CARTYPE_ORBIBOT
        assert pkt[5:11] == bytearray([0, 0, 0, 0, 0, 0])

    def test_forward_motion_encoded(self):
        driver = _make_rosmaster()
        driver.set_car_motion(0.3, 0, 0)  # vx=0.3 m/s
        pkt = self._get_written(driver)
        vx = struct.unpack('<h', bytes(pkt[5:7]))[0]
        assert vx == 300

    def test_lateral_motion_encoded(self):
        driver = _make_rosmaster()
        driver.set_car_motion(0, 0.2, 0)
        pkt = self._get_written(driver)
        vy = struct.unpack('<h', bytes(pkt[7:9]))[0]
        assert vy == 200

    def test_angular_motion_encoded(self):
        driver = _make_rosmaster()
        driver.set_car_motion(0, 0, 1.0)  # 1 rad/s → 1000 mrad/s
        pkt = self._get_written(driver)
        vz = struct.unpack('<h', bytes(pkt[9:11]))[0]
        assert vz == 1000

    def test_checksum_valid(self):
        driver = _make_rosmaster()
        driver.set_car_motion(0.3, 0.1, 0.5)
        pkt = list(self._get_written(driver))
        expected = _checksum(pkt[:-1])
        assert pkt[-1] == expected


# ---------------------------------------------------------------------------
# Command building — reset commands
# ---------------------------------------------------------------------------

class TestResetCommands:
    def _get_written(self, driver):
        return bytearray(driver.ser.write.call_args[0][0])

    def test_reset_odometry_func_code(self):
        driver = _make_rosmaster()
        driver.reset_odometry()
        pkt = self._get_written(driver)
        assert pkt[3] == FUNC_RESET_ODOM

    def test_reset_odometry_no_data(self):
        driver = _make_rosmaster()
        driver.reset_odometry()
        pkt = self._get_written(driver)
        assert len(pkt) == 5   # HEAD DEVID LEN FUNC CHECKSUM

    def test_reset_encoders_func_code(self):
        driver = _make_rosmaster()
        driver.reset_encoders()
        pkt = self._get_written(driver)
        assert pkt[3] == FUNC_RESET_ENCODERS

    def test_reset_encoders_no_data(self):
        driver = _make_rosmaster()
        driver.reset_encoders()
        pkt = self._get_written(driver)
        assert len(pkt) == 5
