#!/usr/bin/env python3
# coding: utf-8

# rosmaster_driver is a ROS 2 node clone from Rosmaster_Lib which is used for communicating
# with the Yahboom ROS Expansion Board V3.
# This driver has been pruned to remove unused features (RGB, Servo, Arm, raw motor control,
# car_run, car_type, version query, PID query) and updated to V3.3.9 standards.
# Matches Yahboom protocol exactly - odometry is calculated on ROS2 side from encoder data.

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
FUNC_RESET_ODOM = 0x09
FUNC_MOTION = 0x12
FUNC_SET_MOTOR_PID = 0x13
FUNC_SET_YAW_PID = 0x14
FUNC_REPORT_ODOM = 0x15
FUNC_SET_MAG_CAL = 0x16
FUNC_SET_MOTOR_PID_MULTILEVEL = 0x18
FUNC_VERSION = 0x51
FUNC_RESET_FLASH = 0xA0

# Car type (OrbiBot uses mecanum only; byte required in MOTION packet format)
CARTYPE_ORBIBOT = 0x07

# ICM-20948 sensor conversion ratios (pre-scaled by firmware, units in milli)
ICM20948_GYRO_RATIO = 1 / 1000.0
ICM20948_ACCEL_RATIO = 1 / 1000.0
ICM20948_MAG_RATIO = 1 / 1000.0

# Radians to degrees
RAD_TO_DEG = 57.2957795


# Driver version / Yahboom protocol compatibility (V3.3.9)
class Rosmaster:

    def __init__(self, car_type=1, com="/dev/motordriver", delay=.002, debug=False):
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

        self._pid_index = 0
        self._kp1 = 0
        self._ki1 = 0
        self._kd1 = 0

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

        if self._debug:
            print("cmd_delay=" + str(self._delay_time) + "s")

        if self.ser.is_open:
            print("Rosmaster Serial Opened! Baudrate=115200")
        else:
            print("Serial Open Failed!")
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

    def _reconnect_serial(self, max_retries=10, retry_delay=1.0):
        """Attempt to reconnect to serial port after disconnect."""
        for attempt in range(max_retries):
            if not self._running:
                return False
            try:
                # Close existing connection if open
                try:
                    self.ser.close()
                except Exception:
                    pass

                time.sleep(retry_delay)

                # Reopen serial port
                self.ser = serial.Serial(self._com_port, 115200, timeout=0.1)
                self.ser.reset_input_buffer()
                print(f"Serial reconnected to {self._com_port} (attempt {attempt + 1})")
                return True
            except serial.SerialException as e:
                print(f"Reconnect attempt {attempt + 1}/{max_retries} failed: {e}")

        print(f"Failed to reconnect after {max_retries} attempts")
        return False

    # Parse data based on frame type (OrbiBot firmware sends ICM-20948 only)
    # Bounds checking to prevent struct.unpack errors on malformed packets
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
        elif ext_type == FUNC_SET_MOTOR_PID:
            if len(ext_data) < 7:
                return
            self._pid_index = struct.unpack('B', bytearray(ext_data[0:1]))[0]
            self._kp1 = struct.unpack('h', bytearray(ext_data[1:3]))[0]
            self._ki1 = struct.unpack('h', bytearray(ext_data[3:5]))[0]
            self._kd1 = struct.unpack('h', bytearray(ext_data[5:7]))[0]
            if self._debug:
                print("FUNC_SET_MOTOR_PID:", self._pid_index, [self._kp1, self._ki1, self._kd1])

        elif ext_type == FUNC_SET_YAW_PID:
            if len(ext_data) < 7:
                return
            self._pid_index = struct.unpack('B', bytearray(ext_data[0:1]))[0]
            self._kp1 = struct.unpack('h', bytearray(ext_data[1:3]))[0]
            self._ki1 = struct.unpack('h', bytearray(ext_data[3:5]))[0]
            self._kd1 = struct.unpack('h', bytearray(ext_data[5:7]))[0]
            if self._debug:
                print("FUNC_SET_YAW_PID:", self._pid_index, [self._kp1, self._ki1, self._kd1])
        elif ext_type == FUNC_VERSION:
            # Parse firmware version response: [major, minor, checksum]
            if len(ext_data) >= 2:
                version_major = ext_data[0]
                version_minor = ext_data[1]
                with self._data_lock:
                    self._firmware_version = f"{version_major}.{version_minor}"
                    self._last_data_timestamp = time.time()

    # Receive data (R6: buffered reads to reduce syscalls)
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

    # Start thread for receiving and processing data
    def create_receive_threading(self):
        try:
            if self._uart_state == 0:
                name1 = "task_serial_receive"
                task_receive = threading.Thread(target=self._receive_data, name=name1)
                task_receive.daemon = True
                task_receive.start()
                print("----------------create receive threading--------------")
                self._uart_state = 1
                time.sleep(.05)
        except Exception as e:
            print(f'---create_receive_threading error: {e}---')

    # MCU automatically returns data status bit (default enabled).
    # forever=True: Permanent (saved to flash), forever=False: Temporary.
    def set_auto_report_state(self, enable, forever=False):
        try:
            self._auto_report_enabled = bool(enable)
            state1 = 1 if enable else 0
            state2 = 0x5F if forever else 0
            self._send_command(FUNC_AUTO_REPORT, [state1, state2])
            if self._debug:
                print("report: auto_report", state1, state2)
        except (serial.SerialException, OSError) as e:
            print(f'---set_auto_report_state error: {e}---')

    # Buzzer: on_time=0 off, 1=always on, >=10 beep for N ms then auto off.
    def set_beep(self, on_time):
        try:
            if on_time < 0:
                print("beep input error!")
                return
            value = bytearray(struct.pack('h', int(on_time)))
            self._send_command(FUNC_BEEP, [value[0], value[1]])
            if self._debug:
                print("beep:", on_time)
        except (serial.SerialException, OSError) as e:
            print(f'---set_beep error: {e}---')

    # Car motion control. v_x=[-1.0, 1.0], v_y=[-1.0, 1.0], v_z=[-5, 5]
    def set_car_motion(self, v_x, v_y, v_z):
        try:
            vx_parms = bytearray(struct.pack('h', int(v_x*1000)))
            vy_parms = bytearray(struct.pack('h', int(v_y*1000)))
            vz_parms = bytearray(struct.pack('h', int(v_z*1000)))
            cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x00, FUNC_MOTION, self._car_type, \
                vx_parms[0], vx_parms[1], vy_parms[0], vy_parms[1], vz_parms[0], vz_parms[1]]
            cmd[2] = len(cmd) - 1
            checksum = sum(cmd, SERIAL_COMPLEMENT) & 0xff
            cmd.append(checksum)
            with self._write_lock:
                self.ser.write(cmd)
            if self._debug:
                print("motion:", cmd)
            time.sleep(self._delay_time)
        except (serial.SerialException, OSError) as e:
            print(f'---set_car_motion error: {e}---')

    # PID parameter control. Affects set_car_motion speed changes. Optional by default.
    # kp ki kd = [0, 10.00], decimals allowed.
    # forever=True: Permanent (saved to flash), forever=False: Temporary.
    # Permanent storage takes time, so delay is added to avoid packet loss.
    # Temporary effect is fast, single use, data lost after restart.
    def set_pid_param(self, kp, ki, kd, forever=False):
        try:
            state = 0
            if forever:
                state = 0x5F
            cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x0A, FUNC_SET_MOTOR_PID]
            if kp > 10 or ki > 10 or kd > 10 or kp < 0 or ki < 0 or kd < 0:
                print("PID value must be:[0, 10.00]")
                return
            kp_params = bytearray(struct.pack('h', int(kp * 1000)))
            ki_params = bytearray(struct.pack('h', int(ki * 1000)))
            kd_params = bytearray(struct.pack('h', int(kd * 1000)))
            cmd.append(kp_params[0])  # low
            cmd.append(kp_params[1])  # high
            cmd.append(ki_params[0])  # low
            cmd.append(ki_params[1])  # high
            cmd.append(kd_params[0])  # low
            cmd.append(kd_params[1])  # high
            cmd.append(state)
            checksum = sum(cmd, SERIAL_COMPLEMENT) & 0xff
            cmd.append(checksum)
            with self._write_lock:
                self.ser.write(cmd)
            if self._debug:
                print("pid:", cmd)
            time.sleep(self._delay_time)
            if forever:
                time.sleep(.1)
        except (serial.SerialException, OSError) as e:
            print(f'---set_pid_param error: {e}---')

    # Set Yaw Angle PID
    def set_yaw_pid_param(self, kp, ki, kd, forever=False):
        try:
            state = 0
            if forever:
                state = 0x5F
            cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x0A, FUNC_SET_YAW_PID]
            if kp > 10 or ki > 10 or kd > 10 or kp < 0 or ki < 0 or kd < 0:
                print("YAW PID value must be:[0, 10.00]")
                return
            kp_params = bytearray(struct.pack('h', int(kp * 1000)))
            ki_params = bytearray(struct.pack('h', int(ki * 1000)))
            kd_params = bytearray(struct.pack('h', int(kd * 1000)))
            cmd.append(kp_params[0])  # low
            cmd.append(kp_params[1])  # high
            cmd.append(ki_params[0])  # low
            cmd.append(ki_params[1])  # high
            cmd.append(kd_params[0])  # low
            cmd.append(kd_params[1])  # high
            cmd.append(state)
            checksum = sum(cmd, SERIAL_COMPLEMENT) & 0xff
            cmd.append(checksum)
            with self._write_lock:
                self.ser.write(cmd)
            if self._debug:
                print("pid:", cmd)
            time.sleep(self._delay_time)
            if forever:
                time.sleep(.1)
        except (serial.SerialException, OSError) as e:
            print(f'---set_yaw_pid_param error: {e}---')

    def set_pid_multilevel(self, thresholds, gains, forever=False):
        """DEPRECATED: Multi-level PID removed. Use set_pid_param() instead."""
        # This method is kept for API compatibility but does nothing
        # Multi-level PID has been removed in favor of single PID
        print("WARNING: Multi-level PID is deprecated. Using single PID via set_pid_param().")
        if len(gains) >= 3:
            # Use Level 1 gains (middle level) as the single PID setting
            self.set_pid_param(gains[3], gains[4], gains[5], forever)

    def set_mag_calibration(self, offset_x, offset_y, offset_z):
        """Set magnetometer hard iron calibration offsets (in µT)."""
        try:
            ox = bytearray(struct.pack('h', int(offset_x * 100)))
            oy = bytearray(struct.pack('h', int(offset_y * 100)))
            oz = bytearray(struct.pack('h', int(offset_z * 100)))
            data = [ox[0], ox[1], oy[0], oy[1], oz[0], oz[1]]
            self._send_command(FUNC_SET_MAG_CAL, data)
            if self._debug:
                print("mag_cal:", offset_x, offset_y, offset_z)
        except (serial.SerialException, OSError) as e:
            print(f'---set_mag_calibration error: {e}---')

    def reset_flash_value(self):
        try:
            self._send_command(FUNC_RESET_FLASH, [0x5F])
            time.sleep(.1)
        except (serial.SerialException, OSError) as e:
            print(f'---reset_flash_value error: {e}---')

    def reset_odometry(self):
        """Reset firmware odometry to zero. (BUG-4: length byte = len(cmd)-1 = 0x03.)"""
        try:
            self._send_command(FUNC_RESET_ODOM, [])
            time.sleep(0.01)
        except (serial.SerialException, OSError) as e:
            print(f'---reset_odometry error: {e}---')

    def get_last_data_timestamp(self):
        """Return timestamp of last successfully parsed firmware packet (for data freshness)."""
        with self._data_lock:
            return self._last_data_timestamp

    # Get accelerometer triaxial data (a_x, a_y, a_z)
    # Uses lock to prevent data tearing
    def get_accelerometer_data(self):
        with self._data_lock:
            return self._ax, self._ay, self._az

    # Get gyroscope triaxial data (g_x, g_y, g_z)
    def get_gyroscope_data(self):
        with self._data_lock:
            return self._gx, self._gy, self._gz

    # Get magnetometer triaxial data (m_x, m_y, m_z)
    def get_magnetometer_data(self):
        with self._data_lock:
            return self._mx, self._my, self._mz

    # Get board attitude angles (yaw, roll, pitch)
    # to_angle=True: return degrees, to_angle=False: return radians
    def get_imu_attitude_data(self, to_angle=True):
        with self._data_lock:
            if to_angle:
                return self._roll * RAD_TO_DEG, self._pitch * RAD_TO_DEG, self._yaw * RAD_TO_DEG
            else:
                return self._roll, self._pitch, self._yaw

    # Get car velocity (val_vx, val_vy, val_vz)
    def get_motion_data(self):
        with self._data_lock:
            return self._vx, self._vy, self._vz

    # Get battery voltage
    def get_battery_voltage(self):
        with self._data_lock:
            return self._battery_voltage / 10.0

    # Get four-channel motor encoder data
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
