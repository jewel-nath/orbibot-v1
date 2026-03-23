# Firmware Changelog

## [Unreleased] — 2026-03-23

### Improvements

- **Accelerometer X/Y bias calibration at startup** (`imu_driver.c`)
  `imu_calibrate()` now calibrates both gyro AND accel offsets from 1000 stationary samples.
  Computes accel X/Y bias (should be ~0 when level) and subtracts in `imu_read_calibrated()`
  and `imu_read_both()`. Accel Z is intentionally NOT corrected — Madgwick needs gravity vector
  (~9.81 m/s²) intact. Inspired by lgdxrobot2 firmware (`imu.c:264-267`) which calibrates both
  sensors at startup. Boot log updated to show computed offsets.
  **⚠️ Requires hardware verification: robot must be stationary and level during boot.**

- **Startup IMU noise variance computation** (`imu_driver.c`, `imu_driver.h`)
  `imu_calibrate()` now computes per-axis variance for accel and gyro using Welford's online
  algorithm during the existing 1000-sample calibration loop. No extra RAM (vs lgdxrobot2's
  500×3 float arrays = 6KB). Values exposed via `imu_get_noise_variance()` for protocol
  reporting. Ready for ROS2 Imu covariance diagonal entries.

- **Encoder anomaly detection** (`task_control.c`, `orbibot_config.h`)
  Wheel speed readings beyond `MAX_WHEEL_SPEED_MMS` (3500 mm/s, 2× theoretical motor max)
  are discarded and replaced with last valid reading. Prevents PID overshoot from EMI spikes
  or loose encoder connections. Inspired by lgdxrobot2 (`motor.c:406-407`).
  New config: `MAX_WHEEL_SPEED_MMS` in `orbibot_config.h`.
  **TODO:** Measure actual per-motor max speed and replace theoretical value.

## [Previous] — 2026-03-22

### Bug Fixes

- **FW-BUG-2 — Checksum loop now includes Device_ID byte** (`protocol.c`)
  Loop start corrected from index 2 to index 1, matching the protocol spec: "additive sum
  of all bytes from Device_ID through last data byte." Previously the Device_ID byte was
  excluded from the checksum, violating the spec and allowing a corrupted Device_ID to pass
  validation silently.

- **FW-BUG-3 — Battery voltage uint8 cast overflow guard** (`protocol.c`)
  Cast now goes through a `uint16_t` intermediate with explicit saturation check at 255
  before narrowing to `uint8_t`. Prevents IEEE 754 rounding from producing 256 on
  borderline values (e.g. 25.50001 × 10 = 255.0001 → was truncating to 255 on most
  compilers but could theoretically overflow).

- **FW-ISSUE-1 — IMU initialization failure now halts boot** (`main.c`)
  Previously, if `imu_driver_init()` returned non-zero (SPI wiring fault, WHO_AM_I
  mismatch), the firmware continued booting and `task_imu` read garbage SPI data that
  silently corrupted odometry. Now the boot sequence halts with a diagnostic message and
  spins until the IWDG watchdog resets the MCU. This makes IMU faults immediately visible
  (boot messages stop; no auto-report stream).

- **FW-DOC-1 — Encoder direction table corrected and cross-referenced** (`encoder_driver.c`)
  `encoder_direction[]` values updated from `{-1, 1, 1, -1}` to `{-1, -1, 1, 1}` to align
  with the PWM direction flags in `hal_timer.c:motor_map[]` (M1=-1, M2=-1, M3=+1, M4=+1).
  M2 and M4 were mismatched, causing odometry drift.
  **⚠️ Requires hardware verification with `python3 tests/test_encoder.py` before deploying.**
  Cross-reference comment added linking `encoder_direction[]` to `motor_map[]`.

### Improvements

- **FW-QUALITY-1 — Vy double negation eliminated** (`protocol.c`, `mecanum_kinematics.c`, `task_control.c`)
  The code previously negated `vy` twice — once in `protocol_handle_motion()` and once in
  `mecanum_inverse_kinematics()` — relying on cancellation. Both negations are removed.
  `robot->vy` now carries the canonical ROS frame convention (positive = left) throughout
  the entire control stack, and the kinematics formula uses it directly. The reported
  measured velocity in `control_get_measured_velocity()` no longer applies the mirroring
  inversion either, for consistent round-trip semantics.

- **FW-LIMIT-1 — Velocity ramp constant renamed and documented** (`orbibot_config.h`, `task_control.c`)
  `MOTOR_SPEED_RAMP_MMS` renamed to `MOTOR_DECEL_RAMP_MMS` to reflect that it only applies
  during deceleration and direction reversal (acceleration remains instant). Extended comment
  explains effective deceleration rate (1000 mm/s²) and how to add acceleration ramping.

- **FW-ISSUE-2 — SPI timeout behaviour documented in imu_read_register()** (`imu_driver.c`)
  Added docblock explaining that `hal_spi_read_byte()` returns `0xFF` on timeout, and why
  the WHO_AM_I identity check at init time naturally rejects bus faults. No per-call
  overhead added at the 50 Hz sensor rate.

- **FW-DOC-2 — YAW_ENABLE_THRESHOLD explanation added** (`orbibot_config.h`)
  Comment now explains the threshold prevents IMU drift from fighting static friction at
  near-zero speed, and documents the empirical tuning rationale (0.05 m/s avoids servo
  chatter).

---

## [2.0.0] — 2026-03-15

- Initial production release (see git log for full history)
