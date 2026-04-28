#!/usr/bin/env python3
"""
ROSMaster Protocol Library for OrbiBot Firmware Testing

Shared protocol definitions and utilities for all test scripts.
ROSMaster compatible serial protocol for firmware testing.

Packet format: [HEAD][DEVICE_ID][LENGTH][FUNC][DATA...][CHECKSUM]
"""

import math
import serial
import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Tuple

# Protocol constants
HEAD = 0xFF
DEVICE_ID = 0xFC         # ID for commands TO firmware
DEVICE_ID_REPLY = 0xFB   # ID for responses FROM firmware
COMPLEMENT = 257 - DEVICE_ID


class FuncCode(IntEnum):
    """Function codes for ROSMaster protocol."""
    AUTO_REPORT = 0x01
    BEEP = 0x02
    SET_RGB = 0x03
    SET_PWM_SERVO = 0x04
    RESET_ENCODERS = 0x08
    SET_MOTOR = 0x09
    REPORT_SPEED = 0x0A
    REPORT_IMU_ATTITUDE = 0x0C
    REPORT_ENCODER = 0x0D
    REPORT_IMU_RAW = 0x0E     # ICM-20948 raw: gyro+accel (12 bytes; mag removed 2026-04-28)
    MOTION = 0x12
    SET_MOTOR_PID = 0x13
    SET_YAW_PID = 0x14
    REPORT_ODOM = 0x15        # Firmware odometry: x,y,theta,vx,vy,omega
    OLED_SET = 0x41
    REQUEST_DATA = 0x50
    VERSION = 0x51


class CarType(IntEnum):
    """Car type definitions."""
    MECANUM = 0x01
    MECANUM_MAX = 0x02
    ORBIBOT = 0x07


@dataclass
class SpeedData:
    """Parsed speed report data."""
    vx_mm: int      # Forward velocity in mm/s
    vy_mm: int      # Lateral velocity in mm/s
    vz_mrad: int    # Angular velocity in mrad/s
    battery_v: float  # Battery voltage in V


@dataclass
class IMURawData:
    """Parsed raw IMU data (ICM-20948).

    Firmware sends 12 bytes: [Gyro X,Y,Z][Accel X,Y,Z], each as int16 LE.
    Magnetometer fields were removed 2026-04-28 — see firmware-changelog.md.
    """
    gyro_x: int
    gyro_y: int
    gyro_z: int
    accel_x: int
    accel_y: int
    accel_z: int


@dataclass
class IMUAttitudeData:
    """Parsed IMU attitude data."""
    roll: float     # Roll angle in degrees
    pitch: float    # Pitch angle in degrees
    yaw: float      # Yaw angle in degrees


@dataclass
class EncoderData:
    """Parsed encoder data."""
    m1: int   # Front-Left
    m2: int   # Back-Left
    m3: int   # Front-Right
    m4: int   # Back-Right


class ROSMasterProtocol:
    """ROSMaster serial protocol handler."""

    def __init__(self, port: str = '/dev/motordriver', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self._rx_buffer = bytearray()

    def connect(self, timeout: float = 1.0) -> bool:
        """Connect to firmware."""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=timeout)
            time.sleep(0.1)
            self.ser.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}")
            return False

    def disconnect(self):
        """Disconnect from firmware."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @staticmethod
    def calculate_checksum(packet: list) -> int:
        """Calculate checksum for packet."""
        return sum(packet, COMPLEMENT) & 0xFF

    def create_packet(self, func_code: int, data: list = None) -> bytes:
        """Create a complete packet with checksum."""
        if data is None:
            data = []
        packet = [HEAD, DEVICE_ID, 0x00, func_code] + data
        packet[2] = len(packet) - 1  # Length excludes HEAD and includes checksum
        checksum = self.calculate_checksum(packet)
        packet.append(checksum)
        return bytes(packet)

    def send(self, func_code: int, data: list = None):
        """Send a command packet."""
        if self.ser:
            packet = self.create_packet(func_code, data)
            self.ser.write(packet)

    def enable_auto_report(self, enable: bool = True):
        """Enable or disable auto-report."""
        self.send(FuncCode.AUTO_REPORT, [0x01 if enable else 0x00, 0x00])
        time.sleep(0.1)

    def send_motion(self, vx_m: float, vy_m: float, vz_rad: float, car_type: int = CarType.MECANUM):
        """Send motion command.

        Args:
            vx_m: Forward velocity in m/s
            vy_m: Lateral velocity in m/s
            vz_rad: Angular velocity in rad/s
            car_type: Robot type
        """
        vx_mm = int(vx_m * 1000)
        vy_mm = int(vy_m * 1000)
        vz_mrad = int(vz_rad * 1000)

        data = [car_type]
        data.extend(struct.pack('<h', vx_mm))
        data.extend(struct.pack('<h', vy_mm))
        data.extend(struct.pack('<h', vz_mrad))
        self.send(FuncCode.MOTION, list(data))

    def stop(self):
        """Stop all motors."""
        self.send_motion(0, 0, 0)

    def beep(self, duration_ms: int = 100):
        """Beep the buzzer."""
        self.send(FuncCode.BEEP, [duration_ms & 0xFF, (duration_ms >> 8) & 0xFF])

    def set_motor(self, motor_id: int, speed: int):
        """Set individual motor speed (-100 to 100)."""
        speed = max(-100, min(100, speed))
        self.send(FuncCode.SET_MOTOR, [motor_id, speed & 0xFF])

    def set_oled(self, line: int, text: str):
        """Set OLED display line (0-3)."""
        text_bytes = text.encode('ascii', errors='ignore')[:16]
        data = [line, len(text_bytes)] + list(text_bytes)
        self.send(FuncCode.OLED_SET, data)

    def read_packets(self, timeout: float = 1.0) -> List[Tuple[int, bytes]]:
        """Read and parse available packets.

        Returns:
            List of (func_code, payload) tuples
        """
        packets = []
        if not self.ser:
            return packets

        deadline = time.time() + timeout

        while time.time() < deadline:
            # Read available data
            if self.ser.in_waiting > 0:
                self._rx_buffer.extend(self.ser.read(self.ser.in_waiting))

            # Parse packets from buffer
            while len(self._rx_buffer) >= 4:
                # Find header
                try:
                    head_idx = self._rx_buffer.index(HEAD)
                    if head_idx > 0:
                        self._rx_buffer = self._rx_buffer[head_idx:]
                except ValueError:
                    self._rx_buffer.clear()
                    break

                if len(self._rx_buffer) < 4:
                    break

                # Check device ID
                if self._rx_buffer[1] != DEVICE_ID_REPLY:
                    self._rx_buffer = self._rx_buffer[1:]
                    continue

                # Get length
                pkt_len = self._rx_buffer[2]
                total_len = pkt_len + 2  # +2 for HEAD and DEVICE_ID

                if len(self._rx_buffer) < total_len:
                    break

                # Extract packet
                packet = self._rx_buffer[:total_len]
                self._rx_buffer = self._rx_buffer[total_len:]

                # Parse
                func_code = packet[3]
                payload = bytes(packet[4:-1])  # Exclude checksum
                packets.append((func_code, payload))

            if packets:
                break

            time.sleep(0.001)

        return packets

    def parse_speed(self, payload: bytes) -> Optional[SpeedData]:
        """Parse REPORT_SPEED payload."""
        if len(payload) < 7:
            return None
        vx = struct.unpack('<h', payload[0:2])[0]
        vy = struct.unpack('<h', payload[2:4])[0]
        vz = struct.unpack('<h', payload[4:6])[0]
        batt = payload[6] * 0.1
        return SpeedData(vx, vy, vz, batt)

    def parse_imu_raw(self, payload: bytes) -> Optional[IMURawData]:
        """Parse REPORT_IMU_RAW payload (12 bytes: gyro+accel, each int16 LE)."""
        if len(payload) < 12:
            return None
        values = struct.unpack('<6h', payload[:12])
        return IMURawData(*values)

    def parse_imu_attitude(self, payload: bytes) -> Optional[IMUAttitudeData]:
        """Parse REPORT_IMU_ATTITUDE payload."""
        if len(payload) < 6:
            return None
        values = struct.unpack('<3h', payload[:6])
        # Firmware sends radians × 10000, convert to degrees
        rad_to_deg = 180.0 / math.pi
        return IMUAttitudeData(
            values[0] / 10000.0 * rad_to_deg,
            values[1] / 10000.0 * rad_to_deg,
            values[2] / 10000.0 * rad_to_deg
        )

    def parse_encoder(self, payload: bytes) -> Optional[EncoderData]:
        """Parse REPORT_ENCODER payload."""
        if len(payload) < 16:
            return None
        values = struct.unpack('<4i', payload[:16])
        return EncoderData(*values)


class PacketMonitor:
    """Utility class for monitoring and counting packets."""

    def __init__(self, protocol: ROSMasterProtocol):
        self.protocol = protocol
        self.packet_counts: Dict[int, int] = {}
        self.total_bytes = 0
        self.total_packets = 0
        self.start_time = 0.0
        self.callbacks: Dict[int, Callable] = {}

    def register_callback(self, func_code: int, callback: Callable):
        """Register a callback for a specific function code."""
        self.callbacks[func_code] = callback

    def start(self):
        """Start monitoring."""
        self.packet_counts.clear()
        self.total_bytes = 0
        self.total_packets = 0
        self.start_time = time.time()

    def process(self, timeout: float = 0.1):
        """Process incoming packets."""
        packets = self.protocol.read_packets(timeout)
        for func_code, payload in packets:
            self.total_packets += 1
            self.total_bytes += len(payload) + 5  # Approximate packet overhead
            self.packet_counts[func_code] = self.packet_counts.get(func_code, 0) + 1

            if func_code in self.callbacks:
                self.callbacks[func_code](payload)

    @property
    def elapsed(self) -> float:
        return time.time() - self.start_time

    @property
    def packet_rate(self) -> float:
        if self.elapsed > 0:
            return self.total_packets / self.elapsed
        return 0.0

    @property
    def byte_rate(self) -> float:
        if self.elapsed > 0:
            return self.total_bytes / self.elapsed
        return 0.0


# ANSI color codes for terminal output
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_success(msg: str):
    print(f"{Color.GREEN}[OK] {msg}{Color.RESET}")


def print_error(msg: str):
    print(f"{Color.RED}[ERROR] {msg}{Color.RESET}")


def print_warning(msg: str):
    print(f"{Color.YELLOW}[WARN] {msg}{Color.RESET}")


def print_info(msg: str):
    print(f"{Color.BLUE}[INFO] {msg}{Color.RESET}")


def print_header(msg: str):
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*60}")
    print(f" {msg}")
    print(f"{'='*60}{Color.RESET}\n")


def format_hex(data: bytes) -> str:
    """Format bytes as hex string."""
    return ' '.join(f'{b:02X}' for b in data)


if __name__ == "__main__":
    # Quick test
    print("ROSMaster Protocol Library")
    print(f"HEAD: 0x{HEAD:02X}")
    print(f"DEVICE_ID: 0x{DEVICE_ID:02X}")
    print(f"DEVICE_ID_REPLY: 0x{DEVICE_ID_REPLY:02X}")
    print("\nFunction codes:")
    for fc in FuncCode:
        print(f"  {fc.name}: 0x{fc.value:02X}")
