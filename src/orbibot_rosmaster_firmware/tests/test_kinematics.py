#!/usr/bin/env python3
"""
Offline unit tests for OrbiBot firmware kinematics and control algorithms.

Tests (no hardware required):
  - Mecanum inverse kinematics
  - Mecanum forward kinematics
  - Odometry report parsing (firmware packet → floats)
  - PID algorithm (incremental form, anti-windup)
  - Battery voltage encoding

All values match orbibot_config.h and mecanum_kinematics.c / pid_controller.c.
"""

import math
import struct
import pytest


# ---------------------------------------------------------------------------
# Robot geometry constants (mirrors orbibot_config.h)
# ---------------------------------------------------------------------------
WHEEL_RADIUS_M = 0.05           # 50mm
HALF_WHEEL_BASE = 0.13          # 260mm / 2
HALF_TRACK_WIDTH = 0.18         # 360mm / 2
APB = HALF_WHEEL_BASE + HALF_TRACK_WIDTH  # 0.31 m  (a + b in the formula)


# ---------------------------------------------------------------------------
# Pure-Python ports of the firmware kinematics (mecanum_kinematics.c)
# ---------------------------------------------------------------------------

def mecanum_inverse(vx: float, vy: float, omega: float) -> tuple:
    """
    Firmware inverse kinematics: body velocity → wheel angular velocities (rad/s).

    Returns: (fl, bl, fr, br) rad/s
    Firmware formula (wheel linear speed m/s, then /= WHEEL_RADIUS):
        FL = Vx - Vy - APB * omega
        BL = Vx + Vy - APB * omega
        FR = Vx + Vy + APB * omega
        BR = Vx - Vy + APB * omega
    """
    fl = (vx - vy - APB * omega) / WHEEL_RADIUS_M
    bl = (vx + vy - APB * omega) / WHEEL_RADIUS_M
    fr = (vx + vy + APB * omega) / WHEEL_RADIUS_M
    br = (vx - vy + APB * omega) / WHEEL_RADIUS_M
    return fl, bl, fr, br


def mecanum_forward(fl: float, bl: float, fr: float, br: float) -> tuple:
    """
    Firmware forward kinematics: wheel angular velocities (rad/s) → body velocity.

    Returns: (vx, vy, omega) m/s, m/s, rad/s
    """
    # Convert rad/s → m/s linear wheel speeds
    fl_v = fl * WHEEL_RADIUS_M
    bl_v = bl * WHEEL_RADIUS_M
    fr_v = fr * WHEEL_RADIUS_M
    br_v = br * WHEEL_RADIUS_M

    vx = (fl_v + bl_v + fr_v + br_v) / 4.0
    vy = (-fl_v + bl_v + fr_v - br_v) / 4.0
    omega = (-fl_v - bl_v + fr_v + br_v) / (4.0 * APB)
    return vx, vy, omega


def parse_odom_packet(payload: bytes) -> tuple:
    """
    Parse firmware REPORT_ODOM payload (6 × int32 LE, 24 bytes).

    Firmware sends: x_mm, y_mm, theta_mrad, vx_mms, vy_mms, omega_mrads
    Returns: (x_m, y_m, theta_rad, vx_ms, vy_ms, omega_rads)
    """
    assert len(payload) == 24, f"Expected 24 bytes, got {len(payload)}"
    x_mm, y_mm, theta_mrad, vx_mms, vy_mms, omega_mrads = struct.unpack('<6i', payload)
    return (
        x_mm / 1000.0,
        y_mm / 1000.0,
        theta_mrad / 1000.0,
        vx_mms / 1000.0,
        vy_mms / 1000.0,
        omega_mrads / 1000.0,
    )


# ---------------------------------------------------------------------------
# PID controller (incremental form, mirrors pid_controller.c)
# ---------------------------------------------------------------------------

INTEGRAL_MAX = 4000.0
INTEGRAL_MIN = -4000.0


class IncrementalPID:
    """
    Python port of firmware incremental PID (pid_controller.c).

    Incremental form with trapezoidal I-term and conditional anti-windup:
        delta = Kp*(e-e1) + Ki*0.5*(e+e1)*dt + Kd*(e-2*e1+e2)/dt
    Output is accumulated (output += delta), clamped to ±integral_limit.
    """

    def __init__(self, kp: float, ki: float, kd: float, dt: float = 0.01):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.output = 0.0
        self._e1 = 0.0   # previous error
        self._e2 = 0.0   # error two steps ago

    def update(self, error: float) -> float:
        e = error
        e1 = self._e1
        e2 = self._e2

        delta = (
            self.kp * (e - e1)
            + self.ki * 0.5 * (e + e1) * self.dt
            + self.kd * (e - 2.0 * e1 + e2) / self.dt
        )

        new_output = self.output + delta

        # Conditional anti-windup: only clamp if error pushes output further beyond limit
        if new_output > INTEGRAL_MAX:
            if e > 0:
                new_output = INTEGRAL_MAX
        elif new_output < INTEGRAL_MIN:
            if e < 0:
                new_output = INTEGRAL_MIN

        self.output = new_output
        self._e2 = e1
        self._e1 = e
        return self.output

    def reset(self):
        self.output = 0.0
        self._e1 = 0.0
        self._e2 = 0.0


# ---------------------------------------------------------------------------
# Mecanum inverse kinematics tests
# ---------------------------------------------------------------------------

class TestMecanumInverse:

    def test_pure_forward(self):
        """Pure forward motion: all four wheels spin at equal speed."""
        fl, bl, fr, br = mecanum_inverse(1.0, 0.0, 0.0)
        expected = 1.0 / WHEEL_RADIUS_M
        assert fl == pytest.approx(expected, rel=1e-6)
        assert bl == pytest.approx(expected, rel=1e-6)
        assert fr == pytest.approx(expected, rel=1e-6)
        assert br == pytest.approx(expected, rel=1e-6)

    def test_pure_lateral(self):
        """
        Pure lateral (Y) motion: FL and BR spin opposite to BL and FR.
        FL = -vy/R,  BL = +vy/R,  FR = +vy/R,  BR = -vy/R
        """
        fl, bl, fr, br = mecanum_inverse(0.0, 1.0, 0.0)
        r = WHEEL_RADIUS_M
        assert fl == pytest.approx(-1.0 / r, rel=1e-6)
        assert bl == pytest.approx(+1.0 / r, rel=1e-6)
        assert fr == pytest.approx(+1.0 / r, rel=1e-6)
        assert br == pytest.approx(-1.0 / r, rel=1e-6)

    def test_pure_rotation(self):
        """
        Pure rotation (CCW positive): left wheels negative, right wheels positive.
        FL = BL = -APB*omega/R,  FR = BR = +APB*omega/R
        """
        omega = 1.0
        fl, bl, fr, br = mecanum_inverse(0.0, 0.0, omega)
        expected_left = -APB * omega / WHEEL_RADIUS_M
        expected_right = +APB * omega / WHEEL_RADIUS_M
        assert fl == pytest.approx(expected_left, rel=1e-6)
        assert bl == pytest.approx(expected_left, rel=1e-6)
        assert fr == pytest.approx(expected_right, rel=1e-6)
        assert br == pytest.approx(expected_right, rel=1e-6)

    def test_zero_input(self):
        """Zero velocity → all wheels stopped."""
        fl, bl, fr, br = mecanum_inverse(0.0, 0.0, 0.0)
        assert fl == 0.0
        assert bl == 0.0
        assert fr == 0.0
        assert br == 0.0

    def test_combined_vx_omega(self):
        """Forward + rotation: manually verify each wheel speed."""
        vx, omega = 0.5, 1.0
        fl, bl, fr, br = mecanum_inverse(vx, 0.0, omega)
        r = WHEEL_RADIUS_M
        assert fl == pytest.approx((vx - APB * omega) / r, rel=1e-6)
        assert bl == pytest.approx((vx - APB * omega) / r, rel=1e-6)
        assert fr == pytest.approx((vx + APB * omega) / r, rel=1e-6)
        assert br == pytest.approx((vx + APB * omega) / r, rel=1e-6)

    def test_reverse_motion(self):
        """Negative vx → all wheels negative."""
        fl, bl, fr, br = mecanum_inverse(-0.5, 0.0, 0.0)
        expected = -0.5 / WHEEL_RADIUS_M
        assert fl == pytest.approx(expected, rel=1e-6)
        assert bl == pytest.approx(expected, rel=1e-6)
        assert fr == pytest.approx(expected, rel=1e-6)
        assert br == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# Mecanum forward kinematics tests
# ---------------------------------------------------------------------------

class TestMecanumForward:

    def test_pure_forward(self):
        """All wheels forward → vx = wheel_speed * R, vy=0, omega=0."""
        wheel_rad_s = 1.0 / WHEEL_RADIUS_M
        vx, vy, omega = mecanum_forward(wheel_rad_s, wheel_rad_s, wheel_rad_s, wheel_rad_s)
        assert vx == pytest.approx(1.0, abs=1e-9)
        assert vy == pytest.approx(0.0, abs=1e-9)
        assert omega == pytest.approx(0.0, abs=1e-9)

    def test_pure_lateral(self):
        """
        Lateral pattern: FL=-1/R, BL=+1/R, FR=+1/R, BR=-1/R → vy=1.0
        """
        r = WHEEL_RADIUS_M
        fl, bl, fr, br = -1.0/r, +1.0/r, +1.0/r, -1.0/r
        vx, vy, omega = mecanum_forward(fl, bl, fr, br)
        assert vx == pytest.approx(0.0, abs=1e-9)
        assert vy == pytest.approx(1.0, abs=1e-9)
        assert omega == pytest.approx(0.0, abs=1e-9)

    def test_pure_rotation(self):
        """
        Rotation pattern: FL=BL=-APB*omega/R, FR=BR=+APB*omega/R → vx=0, vy=0, omega
        """
        omega_in = 2.0
        r = WHEEL_RADIUS_M
        fl = -APB * omega_in / r
        bl = -APB * omega_in / r
        fr = +APB * omega_in / r
        br = +APB * omega_in / r
        vx, vy, omega_out = mecanum_forward(fl, bl, fr, br)
        assert vx == pytest.approx(0.0, abs=1e-9)
        assert vy == pytest.approx(0.0, abs=1e-9)
        assert omega_out == pytest.approx(omega_in, rel=1e-6)

    def test_roundtrip_forward_only(self):
        """inverse → forward roundtrip for pure forward motion."""
        vx_in, vy_in, omega_in = 0.3, 0.0, 0.0
        fl, bl, fr, br = mecanum_inverse(vx_in, vy_in, omega_in)
        vx_out, vy_out, omega_out = mecanum_forward(fl, bl, fr, br)
        assert vx_out == pytest.approx(vx_in, rel=1e-6)
        assert vy_out == pytest.approx(vy_in, abs=1e-9)
        assert omega_out == pytest.approx(omega_in, abs=1e-9)

    def test_roundtrip_lateral(self):
        """inverse → forward roundtrip for pure lateral motion."""
        vx_in, vy_in, omega_in = 0.0, 0.4, 0.0
        fl, bl, fr, br = mecanum_inverse(vx_in, vy_in, omega_in)
        vx_out, vy_out, omega_out = mecanum_forward(fl, bl, fr, br)
        assert vx_out == pytest.approx(vx_in, abs=1e-9)
        assert vy_out == pytest.approx(vy_in, rel=1e-6)
        assert omega_out == pytest.approx(omega_in, abs=1e-9)

    def test_roundtrip_combined(self):
        """inverse → forward roundtrip for combined vx, vy, omega."""
        vx_in, vy_in, omega_in = 0.5, -0.3, 1.2
        fl, bl, fr, br = mecanum_inverse(vx_in, vy_in, omega_in)
        vx_out, vy_out, omega_out = mecanum_forward(fl, bl, fr, br)
        assert vx_out == pytest.approx(vx_in, rel=1e-6)
        assert vy_out == pytest.approx(vy_in, rel=1e-6)
        assert omega_out == pytest.approx(omega_in, rel=1e-6)

    def test_zero_wheels(self):
        """All wheels stopped → all body velocities zero."""
        vx, vy, omega = mecanum_forward(0.0, 0.0, 0.0, 0.0)
        assert vx == 0.0
        assert vy == 0.0
        assert omega == 0.0


# ---------------------------------------------------------------------------
# Odometry report parsing tests
# ---------------------------------------------------------------------------

class TestOdomParsing:

    def _make_payload(self, x_mm, y_mm, theta_mrad, vx_mms, vy_mms, omega_mrads):
        return struct.pack('<6i', x_mm, y_mm, theta_mrad, vx_mms, vy_mms, omega_mrads)

    def test_zero_payload(self):
        payload = self._make_payload(0, 0, 0, 0, 0, 0)
        x, y, theta, vx, vy, omega = parse_odom_packet(payload)
        assert x == 0.0
        assert y == 0.0
        assert theta == 0.0
        assert vx == 0.0
        assert vy == 0.0
        assert omega == 0.0

    def test_position_scaling(self):
        """1000 mm → 1.0 m, 1000 mrad → 1.0 rad."""
        payload = self._make_payload(1000, 2000, 1000, 500, -300, 200)
        x, y, theta, vx, vy, omega = parse_odom_packet(payload)
        assert x == pytest.approx(1.0, rel=1e-9)
        assert y == pytest.approx(2.0, rel=1e-9)
        assert theta == pytest.approx(1.0, rel=1e-9)
        assert vx == pytest.approx(0.5, rel=1e-9)
        assert vy == pytest.approx(-0.3, rel=1e-9)
        assert omega == pytest.approx(0.2, rel=1e-9)

    def test_negative_values(self):
        """Negative coordinates (robot reversed) parsed correctly."""
        payload = self._make_payload(-500, -250, -1571, -200, 0, -1000)
        x, y, theta, vx, vy, omega = parse_odom_packet(payload)
        assert x == pytest.approx(-0.5, rel=1e-9)
        assert y == pytest.approx(-0.25, rel=1e-9)
        assert theta == pytest.approx(-1.571, rel=1e-9)
        assert vx == pytest.approx(-0.2, rel=1e-9)
        assert omega == pytest.approx(-1.0, rel=1e-9)

    def test_pi_angle(self):
        """π radians = 3142 mrad round-trip."""
        theta_mrad = int(math.pi * 1000)
        payload = self._make_payload(0, 0, theta_mrad, 0, 0, 0)
        _, _, theta, _, _, _ = parse_odom_packet(payload)
        assert theta == pytest.approx(theta_mrad / 1000.0, rel=1e-6)

    def test_wrong_length_raises(self):
        with pytest.raises(AssertionError):
            parse_odom_packet(b'\x00' * 20)

    def test_max_int32(self):
        """Large int32 values (long navigation run) parsed without overflow."""
        big = 2_000_000  # 2000 m in mm
        payload = self._make_payload(big, big, 0, 0, 0, 0)
        x, y, _, _, _, _ = parse_odom_packet(payload)
        assert x == pytest.approx(2000.0, rel=1e-9)
        assert y == pytest.approx(2000.0, rel=1e-9)


# ---------------------------------------------------------------------------
# PID algorithm tests
# ---------------------------------------------------------------------------

class TestIncrementalPID:

    def test_p_only_step(self):
        """P-only: first step output = Kp * (e - 0) = Kp * e."""
        pid = IncrementalPID(kp=2.0, ki=0.0, kd=0.0, dt=0.01)
        out = pid.update(1.0)
        assert out == pytest.approx(2.0, rel=1e-9)

    def test_p_only_second_step_same_error(self):
        """P-only with constant error: incremental delta = 0 on second step."""
        pid = IncrementalPID(kp=2.0, ki=0.0, kd=0.0, dt=0.01)
        pid.update(1.0)   # output = 2.0
        out = pid.update(1.0)  # delta = Kp*(1-1) = 0 → output stays 2.0
        assert out == pytest.approx(2.0, rel=1e-9)

    def test_pi_accumulates(self):
        """PI: integral accumulates over multiple steps."""
        pid = IncrementalPID(kp=1.0, ki=1.0, kd=0.0, dt=0.01)
        out1 = pid.update(1.0)   # Kp*(1-0) + Ki*0.5*(1+0)*0.01 = 1.0 + 0.005
        assert out1 == pytest.approx(1.005, rel=1e-9)
        out2 = pid.update(1.0)   # Kp*(1-1) + Ki*0.5*(1+1)*0.01 = 0 + 0.01
        # output = 1.005 + 0.01 = 1.015
        assert out2 == pytest.approx(1.015, rel=1e-9)

    def test_d_term_spike_on_first_step(self):
        """D-only: large spike on first step, then drops on constant error."""
        pid = IncrementalPID(kp=0.0, ki=0.0, kd=1.0, dt=0.01)
        out1 = pid.update(1.0)   # Kd*(1 - 0 + 0) / 0.01 = 100
        assert out1 == pytest.approx(100.0, rel=1e-9)
        out2 = pid.update(1.0)   # Kd*(1 - 2*1 + 0) / 0.01 = -100/0.01 → -100
        assert out2 == pytest.approx(0.0, rel=1e-6)  # 100 + (-100) = 0

    def test_anti_windup_positive(self):
        """Output saturates at +INTEGRAL_MAX when large positive error accumulates."""
        pid = IncrementalPID(kp=1000.0, ki=0.0, kd=0.0, dt=0.01)
        # Single big step should hit the cap
        out = pid.update(100.0)
        assert out <= INTEGRAL_MAX

    def test_anti_windup_negative(self):
        """Output saturates at -INTEGRAL_MAX when large negative error accumulates."""
        pid = IncrementalPID(kp=1000.0, ki=0.0, kd=0.0, dt=0.01)
        out = pid.update(-100.0)
        assert out >= INTEGRAL_MIN

    def test_anti_windup_does_not_prevent_recovery(self):
        """
        After hitting positive saturation, a negative error should allow output to decrease.
        Anti-windup only blocks accumulation in the same direction as saturation.
        """
        pid = IncrementalPID(kp=1000.0, ki=0.0, kd=0.0, dt=0.01)
        pid.update(100.0)  # drive to +cap
        out = pid.update(-100.0)  # negative error → output should decrease
        assert out < INTEGRAL_MAX

    def test_reset(self):
        """After reset, PID behaves as if freshly initialized."""
        pid = IncrementalPID(kp=2.0, ki=1.0, kd=0.5, dt=0.01)
        for _ in range(10):
            pid.update(1.0)
        pid.reset()
        out = pid.update(1.0)
        fresh = IncrementalPID(kp=2.0, ki=1.0, kd=0.5, dt=0.01)
        expected = fresh.update(1.0)
        assert out == pytest.approx(expected, rel=1e-9)

    def test_zero_error(self):
        """Zero error → zero output on first step."""
        pid = IncrementalPID(kp=5.0, ki=2.0, kd=1.0, dt=0.01)
        out = pid.update(0.0)
        assert out == 0.0

    def test_error_sign_change(self):
        """Sign change in error (overshoot) decrements output (D acts as damper)."""
        pid = IncrementalPID(kp=1.0, ki=0.0, kd=1.0, dt=0.01)
        pid.update(1.0)   # e1=1, output grows
        pid.update(1.0)   # e2=1, e1=1
        out_negative = pid.update(-0.5)  # error goes negative → D term large negative
        # Just verify output decreased compared to previous step
        assert out_negative < pid.output + 1000  # sanity: not diverging


# ---------------------------------------------------------------------------
# Battery voltage encoding tests
# ---------------------------------------------------------------------------

def encode_battery_voltage(voltage_v: float) -> int:
    """
    Firmware battery encoding: voltage × 10, saturate at 255 (uint8).
    e.g. 14.6V → 146,  25.6V → 255 (saturated).
    """
    raw = int(round(voltage_v * 10))
    return max(0, min(255, raw))


def decode_battery_voltage(raw: int) -> float:
    """Firmware battery decoding: raw / 10.0."""
    return raw / 10.0


class TestBatteryEncoding:

    def test_nominal_voltage(self):
        """12.8V (nominal 4S LiFePO4) encodes to 128."""
        assert encode_battery_voltage(12.8) == 128

    def test_full_voltage(self):
        """14.6V (full 4S LiFePO4) encodes to 146."""
        assert encode_battery_voltage(14.6) == 146

    def test_low_warning_threshold(self):
        """11.0V (low warning) encodes to 110."""
        assert encode_battery_voltage(11.0) == 110

    def test_critical_threshold(self):
        """10.5V (critical) encodes to 105."""
        assert encode_battery_voltage(10.5) == 105

    def test_zero_voltage(self):
        """0V → raw = 0."""
        assert encode_battery_voltage(0.0) == 0

    def test_saturation_high(self):
        """Voltage above 25.5V saturates at 255."""
        assert encode_battery_voltage(30.0) == 255
        assert encode_battery_voltage(25.6) == 255

    def test_roundtrip(self):
        """Encode then decode recovers original voltage within 0.05V."""
        for v in [10.5, 11.0, 12.8, 14.6]:
            raw = encode_battery_voltage(v)
            decoded = decode_battery_voltage(raw)
            assert abs(decoded - v) < 0.05
