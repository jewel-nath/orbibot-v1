#!/usr/bin/env python3
# coding: utf-8

# Serial driver for Yahboom ROSMaster V3.0 expansion board (STM32F103RCT6).
# Handles binary protocol at 115200 baud for motor control, sensor data, and PID tuning.
# Based on Yahboom Rosmaster_Lib, stripped to OrbiBot essentials.

import struct
import time
import serial
import threading

# Serial protocol constants
SERIAL_HEAD = 0xFF
SERIAL_DEVICE_ID = 0xFC
SERIAL_COMPLEMENT = 257 - SERIAL_DEVICE_ID

# Function codes (Yahboom protocol) — OrbiBot uses ICM-20948 only
FUNC_AUTO_REPORT = 0x01
FUNC_BEEP = 0x02
FUNC_REPORT_SPEED = 0x0A
FUNC_REPORT_IMU_ATT = 0x0C
FUNC_REPORT_ENCODER = 0x0D
FUNC_REPORT_ICM_RAW = 0x0E
FUNC_RESET_ENCODERS = 0x08
FUNC_RESET_ODOM = 0x09
FUNC_MOTION = 0x12
FUNC_SET_MOTOR_PID = 0x13
FUNC_SET_YAW_PID = 0x14
FUNC_REPORT_ODOM = 0x15
FUNC_SET_MAG_CAL = 0x16
FUNC_VERSION = 0x51

# Car type (OrbiBot uses mecanum only; byte required in MOTION packet format)
CARTYPE_ORBIBOT = 0x07

# ICM-20948 sensor conversion ratios
# Gyro/accel: firmware pre-scales calibrated values to milli-units (×1000) before
# sending; driver divides by 1000 to recover SI units.
#   Gyro  ±500 dps  → firmware sends milli-rad/s  → ÷1000 → rad/s
#   Accel ±2 g      → firmware sends milli-m/s²   → ÷1000 → m/s²
# Mag: firmware sends raw AK09916 ADC counts; AK09916 sensitivity = 0.15 µT/count.
#   hardware_node.py then converts µT → Tesla via ×1e-6.
ICM20948_GYRO_RATIO  = 1 / 1000.0   # milli-rad/s → rad/s
ICM20948_ACCEL_RATIO = 1 / 1000.0   # milli-m/s²  → m/s²
ICM20948_MAG_RATIO   = 0.15         # AK09916 raw counts → µT

# Radians to degrees
RAD_TO_DEG = 57.2957795


class Rosmaster:

    def __init__(self, car_type=CARTYPE_ORBIBOT, com="/dev/motordriver", delay=.002, debug=False):
        self._com_port = com
        self._running = True  # Flag to control receive thread

        # Handle serial port open exceptions
        try:
            # Add serial timeout to prevent blocking forever on disconnect
            self.ser = serial.Serial(com, 115200, timeout=0.1)
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open serial port {com}: {e}")

        # Thread lock for encoder/IMU data access
        self._data_lock = threading.Lock()
        # Thread lock for serial port writes (prevent packet interleaving)
        self._write_lock = threading.Lock()

        self._delay_time = delay
        self._debug = debug
        self._car_type = car_type
        self._uart_state = 0

        self._ax = 0.0
        self._ay = 0.0
        self._az = 0.0
        self._gx = 0.0
        self._gy = 0.0
        self._gz = 0.0
        self._mx = 0.0
        self._my = 0.0
        self._mz = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._vz = 0.0

        self._yaw = 0.0
        self._roll = 0.0
        self._pitch = 0.0

        self._encoder_m1 = 0
        self._encoder_m2 = 0
        self._encoder_m3 = 0
        self._encoder_m4 = 0

        self._auto_report_enabled = False  # Track state for reconnect restoration

        # Data freshness for S1/S2 (timestamp of last successfully parsed packet)
        self._last_data_timestamp = 0.0

        self._battery_voltage = 0

        # Firmware version (parsed from FUNC_VERSION response)
        self._firmware_version = "unknown"

        # Firmware odometry (x, y, theta in m/rad; vx, vy, omega in m/s, rad/s)
        self._odom_x = 0.0
        self._odom_y = 0.0
        self._odom_theta = 0.0
        self._odom_vx = 0.0
        self._odom_vy = 0.0
        self._odom_omega = 0.0

        if self.ser.is_open:
            if self._debug:
                print(f"Rosmaster serial opened: {com} @ 115200 baud (delay={delay}s)")
        else:
            print(f"Rosmaster serial open failed: {com}")
        time.sleep(.002)

    def close(self):
        """Stop the receive thread and close the serial port cleanly."""
        self._running = False
        self._uart_state = 0
        try:
            self.ser.close()
        except Exception:
            pass

    def __del__(self):
        self.close()

    def _reconnect_serial(self, max_retries=10, retry_delay=2.0):
        """Attempt to reconnect to serial port after disconnect. Uses backoff to give USB/device time to recover."""
        for attempt in range(max_retries):
            if not self._running:
                return False
            try:
                # Close existing connection if open
                try:
                    self.ser.close()
                except Exception:
                    pass

                # Backoff: 2s, 3s, 4.5s, ... (cap ~15s) so device can re-enumerate after reset
                delay = retry_delay * (1.5 ** min(attempt, 6))
                time.sleep(delay)

                # Reopen serial port
                self.ser = serial.Serial(self._com_port, 115200, timeout=0.1)
                self.ser.reset_input_buffer()
                print(f"Serial reconnected to {self._com_port} (attempt {attempt + 1}/{max_retries})")
                return True
            except serial.SerialException as e:
                print(f"Reconnect attempt {attempt + 1}/{max_retries} failed: {e}")

        print(f"Failed to reconnect after {max_retries} attempts — check USB cable and /dev/motordriver")
        return False

    def _parse_data(self, ext_type, ext_data):
        if ext_type == FUNC_REPORT_SPEED:
            if len(ext_data) < 7:
                return
            with self._data_lock:
                self._vx = int(struct.unpack('h', bytearray(ext_data[0:2]))[0]) / 1000.0
                self._vy = int(struct.unpack('h', bytearray(ext_data[2:4]))[0]) / 1000.0
                self._vz = int(struct.unpack('h', bytearray(ext_data[4:6]))[0]) / 1000.0
                self._battery_voltage = struct.unpack('B', bytearray(ext_data[6:7]))[0]
                self._last_data_timestamp = time.time()
        elif ext_type == FUNC_REPORT_ICM_RAW:
            if len(ext_data) < 18:
                return
            with self._data_lock:
                self._gx = struct.unpack('h', bytearray(ext_data[0:2]))[0] * ICM20948_GYRO_RATIO
                self._gy = struct.unpack('h', bytearray(ext_data[2:4]))[0] * ICM20948_GYRO_RATIO
                self._gz = struct.unpack('h', bytearray(ext_data[4:6]))[0] * ICM20948_GYRO_RATIO
                self._ax = struct.unpack('h', bytearray(ext_data[6:8]))[0] * ICM20948_ACCEL_RATIO
                self._ay = struct.unpack('h', bytearray(ext_data[8:10]))[0] * ICM20948_ACCEL_RATIO
                self._az = struct.unpack('h', bytearray(ext_data[10:12]))[0] * ICM20948_ACCEL_RATIO
                self._mx = struct.unpack('h', bytearray(ext_data[12:14]))[0] * ICM20948_MAG_RATIO
                self._my = struct.unpack('h', bytearray(ext_data[14:16]))[0] * ICM20948_MAG_RATIO
                self._mz = struct.unpack('h', bytearray(ext_data[16:18]))[0] * ICM20948_MAG_RATIO
                self._last_data_timestamp = time.time()
        elif ext_type == FUNC_REPORT_IMU_ATT:
            if len(ext_data) < 6:
                return
            with self._data_lock:
                self._roll = struct.unpack('h', bytearray(ext_data[0:2]))[0] / 10000.0
                self._pitch = struct.unpack('h', bytearray(ext_data[2:4]))[0] / 10000.0
                self._yaw = struct.unpack('h', bytearray(ext_data[4:6]))[0] / 10000.0
                self._last_data_timestamp = time.time()
        elif ext_type == FUNC_REPORT_ENCODER:
            if len(ext_data) < 16:
                return
            with self._data_lock:
                self._encoder_m1 = struct.unpack('i', bytearray(ext_data[0:4]))[0]
                self._encoder_m2 = struct.unpack('i', bytearray(ext_data[4:8]))[0]
                self._encoder_m3 = struct.unpack('i', bytearray(ext_data[8:12]))[0]
                self._encoder_m4 = struct.unpack('i', bytearray(ext_data[12:16]))[0]
                self._last_data_timestamp = time.time()
        elif ext_type == FUNC_REPORT_ODOM:
            if len(ext_data) < 24:
                return
            vals = struct.unpack('<6i', bytearray(ext_data[0:24]))
            with self._data_lock:
                self._odom_x = vals[0] / 1000.0       # mm → m
                self._odom_y = vals[1] / 1000.0       # mm → m
                self._odom_theta = vals[2] / 1000.0   # mrad → rad
                self._odom_vx = vals[3] / 1000.0      # mm/s → m/s
                self._odom_vy = vals[4] / 1000.0      # mm/s → m/s
                self._odom_omega = vals[5] / 1000.0   # mrad/s → rad/s
                self._last_data_timestamp = time.time()
        elif ext_type == FUNC_VERSION:
            # Parse firmware version response: [major, minor, checksum]
            if len(ext_data) >= 2:
                version_major = ext_data[0]
                version_minor = ext_data[1]
                with self._data_lock:
                    self._firmware_version = f"{version_major}.{version_minor}"
                    self._last_data_timestamp = time.time()

    def _receive_data(self):
        self.ser.reset_input_buffer()
        buf = bytearray()
        frame_header_len = 4  # HEAD, DEVID-1, LEN, TYPE
        while self._running:
            try:
                # Read all available bytes
                n = self.ser.in_waiting
                if n > 0:
                    buf.extend(self.ser.read(n))
                elif len(buf) == 0:
                    # Nothing to parse, yield to avoid busy loop
                    time.sleep(0.001)
                    continue

                # Parse one frame if we have enough data
                if len(buf) < frame_header_len:
                    time.sleep(0.001)
                    continue
                if buf[0] != SERIAL_HEAD or buf[1] != SERIAL_DEVICE_ID - 1:
                    buf.pop(0)
                    continue
                ext_len = buf[2]
                frame_len = 2 + ext_len  # LEN byte counts TYPE + data (incl. checksum)
                if ext_len < 2 or frame_len > 256:
                    buf.pop(0)
                    continue
                if len(buf) < frame_len:
                    time.sleep(0.001)
                    continue
                ext_type = buf[3]
                ext_data = list(buf[4:frame_len])
                check_sum = ext_len + ext_type + sum(ext_data[:-1])
                rx_check_num = ext_data[-1]
                if check_sum % 256 == rx_check_num:
                    self._parse_data(ext_type, ext_data)
                elif self._debug:
                    print("check sum error:", ext_len, ext_type, ext_data)
                del buf[:frame_len]
            except (serial.SerialException, OSError) as e:
                print(f"Serial error in receive thread: {e}")
                buf.clear()
                if self._running and self._reconnect_serial():
                    time.sleep(1.0)  # give device time after reopen before first read
                    if self._auto_report_enabled:
                        self.set_auto_report_state(True)
                    print("Receive thread resuming after reconnect")
                    continue
                else:
                    print("Receive thread exiting - reconnect failed or shutdown requested")
                    break

    def _send_command(self, func_code, data_bytes):
        """Build and send a packet: HEAD, DEVID, LEN, FUNC, [data...], checksum. (R5/Q13)"""
        cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x00, func_code] + list(data_bytes)
        cmd[2] = len(cmd) - 1
        checksum = sum(cmd, SERIAL_COMPLEMENT) & 0xff
        cmd.append(checksum)
        with self._write_lock:
            self.ser.write(bytearray(cmd))
        time.sleep(self._delay_time)

    def create_receive_threading(self):
        """Start daemon thread for receiving serial data from firmware."""
        try:
            if self._uart_state == 0:
                task_receive = threading.Thread(
                    target=self._receive_data, name="task_serial_receive", daemon=True)
                task_receive.start()
                self._uart_state = 1
                time.sleep(.05)
        except Exception as e:
            print(f'---create_receive_threading error: {e}---')

    def set_auto_report_state(self, enable, forever=False):
        """Enable/disable firmware auto-report. forever=True saves to flash."""
        try:
            self._auto_report_enabled = bool(enable)
            state1 = 1 if enable else 0
            state2 = 0x5F if forever else 0
            self._send_command(FUNC_AUTO_REPORT, [state1, state2])
        except (serial.SerialException, OSError) as e:
            print(f'---set_auto_report_state error: {e}---')

    def set_beep(self, on_time):
        """Buzzer control: 0=off, 1=continuous, >=10=beep for N ms."""
        if on_time < 0:
            raise ValueError(f"set_beep: on_time must be >= 0, got {on_time}")
        try:
            value = bytearray(struct.pack('h', int(on_time)))
            self._send_command(FUNC_BEEP, [value[0], value[1]])
        except (serial.SerialException, OSError) as e:
            print(f'---set_beep error: {e}---')

    def set_car_motion(self, v_x, v_y, v_z):
        """Send velocity command. vx/vy in m/s [-1.0, 1.0], vz in rad/s [-5, 5]."""
        try:
            vx_b = bytearray(struct.pack('h', int(v_x * 1000)))
            vy_b = bytearray(struct.pack('h', int(v_y * 1000)))
            vz_b = bytearray(struct.pack('h', int(v_z * 1000)))
            data = [self._car_type, vx_b[0], vx_b[1], vy_b[0], vy_b[1], vz_b[0], vz_b[1]]
            self._send_command(FUNC_MOTION, data)
        except (serial.SerialException, OSError) as e:
            print(f'---set_car_motion error: {e}---')

    def _send_pid(self, func_code, kp, ki, kd, forever=False):
        """Send PID gains to firmware. kp/ki/kd in [0, 10.0]. forever=True saves to flash."""
        if kp > 10 or ki > 10 or kd > 10 or kp < 0 or ki < 0 or kd < 0:
            raise ValueError("PID values must be in [0, 10.00]")
        try:
            kp_b = bytearray(struct.pack('h', int(kp * 1000)))
            ki_b = bytearray(struct.pack('h', int(ki * 1000)))
            kd_b = bytearray(struct.pack('h', int(kd * 1000)))
            state = 0x5F if forever else 0
            data = [kp_b[0], kp_b[1], ki_b[0], ki_b[1], kd_b[0], kd_b[1], state]
            self._send_command(func_code, data)
            if forever:
                time.sleep(0.1)  # Flash write needs time
        except (serial.SerialException, OSError) as e:
            print(f'---_send_pid error: {e}---')

    def set_pid_param(self, kp, ki, kd, forever=False):
        """Set motor PID gains. forever=True saves to flash (persists across reboot)."""
        self._send_pid(FUNC_SET_MOTOR_PID, kp, ki, kd, forever)

    def set_yaw_pid_param(self, kp, ki, kd, forever=False):
        """Set yaw PID gains. forever=True saves to flash (persists across reboot)."""
        self._send_pid(FUNC_SET_YAW_PID, kp, ki, kd, forever)

    # Maximum magnetometer offset in µT that fits in int16 with ×100 scaling.
    _MAG_OFFSET_MAX_UT = 327.67

    def set_mag_calibration(self, offset_x, offset_y, offset_z):
        """Set magnetometer hard iron calibration offsets (in µT).

        Args:
            offset_x/y/z: Hard-iron bias in µT. Must be in [-327.67, +327.67].
        Raises:
            ValueError: if any offset is outside the int16 representable range.
        """
        for name, val in (('offset_x', offset_x), ('offset_y', offset_y), ('offset_z', offset_z)):
            if abs(val) > self._MAG_OFFSET_MAX_UT:
                raise ValueError(
                    f"set_mag_calibration: {name}={val} µT out of range "
                    f"[-{self._MAG_OFFSET_MAX_UT}, +{self._MAG_OFFSET_MAX_UT}]")
        try:
            ox = bytearray(struct.pack('h', int(offset_x * 100)))
            oy = bytearray(struct.pack('h', int(offset_y * 100)))
            oz = bytearray(struct.pack('h', int(offset_z * 100)))
            data = [ox[0], ox[1], oy[0], oy[1], oz[0], oz[1]]
            self._send_command(FUNC_SET_MAG_CAL, data)
        except (serial.SerialException, OSError) as e:
            print(f'---set_mag_calibration error: {e}---')

    def reset_odometry(self):
        """Reset firmware odometry to zero. (BUG-4: length byte = len(cmd)-1 = 0x03.)"""
        try:
            self._send_command(FUNC_RESET_ODOM, [])
            time.sleep(0.01)
        except (serial.SerialException, OSError) as e:
            print(f'---reset_odometry error: {e}---')

    def reset_encoders(self):
        """Reset encoder counts to zero on the MCU. Odometry is unchanged."""
        try:
            self._send_command(FUNC_RESET_ENCODERS, [])
            time.sleep(0.01)
        except (serial.SerialException, OSError) as e:
            print(f'---reset_encoders error: {e}---')

    def get_last_data_timestamp(self):
        """Return timestamp of last successfully parsed firmware packet (for data freshness)."""
        with self._data_lock:
            return self._last_data_timestamp

    def get_accelerometer_data(self):
        """Return (ax, ay, az) in m/s^2."""
        with self._data_lock:
            return self._ax, self._ay, self._az

    def get_gyroscope_data(self):
        """Return (gx, gy, gz) in rad/s."""
        with self._data_lock:
            return self._gx, self._gy, self._gz

    def get_magnetometer_data(self):
        """Return (mx, my, mz) in uT."""
        with self._data_lock:
            return self._mx, self._my, self._mz

    def get_imu_attitude_data(self, to_angle=True):
        with self._data_lock:
            if to_angle:
                return self._roll * RAD_TO_DEG, self._pitch * RAD_TO_DEG, self._yaw * RAD_TO_DEG
            else:
                return self._roll, self._pitch, self._yaw

    def get_motion_data(self):
        with self._data_lock:
            return self._vx, self._vy, self._vz

    def get_battery_voltage(self):
        with self._data_lock:
            return self._battery_voltage / 10.0

    def get_motor_encoder(self):
        with self._data_lock:
            return self._encoder_m1, self._encoder_m2, self._encoder_m3, self._encoder_m4

    def get_firmware_odometry(self):
        """Get firmware-side odometry (x, y, theta, vx, vy, omega)."""
        with self._data_lock:
            return (self._odom_x, self._odom_y, self._odom_theta,
                    self._odom_vx, self._odom_vy, self._odom_omega)

    def get_firmware_version(self):
        """Get firmware version string (e.g., '2.0' for v2.0.0)."""
        with self._data_lock:
            return self._firmware_version

    def request_firmware_version(self, timeout=0.5):
        """Send a version request to the firmware and return the version string.

        Sends the 0x51 VERSION command; the receive thread parses the response
        and updates the cached version. Returns the version after waiting.

        Args:
            timeout: Seconds to wait for the firmware response.

        Returns:
            Version string (e.g., '2.0') or 'unknown' if no response.
        """
        try:
            self._send_command(FUNC_VERSION, [])
            time.sleep(timeout)
        except (serial.SerialException, OSError) as e:
            print(f'---request_firmware_version error: {e}---')
        return self.get_firmware_version()
