# Hardware Node Changelog

## [Unreleased] — 2026-03-25

### Refactoring

- **Remove dead code from rosmaster_driver.py**
  Removed: `FUNC_SET_MOTOR_PID_MULTILEVEL` (firmware removed), `FUNC_RESET_FLASH` +
  `reset_flash_value()` (never called), `set_pid_multilevel()` (deprecated stub),
  PID readback fields (`_pid_index`, `_kp1`, `_ki1`, `_kd1`) — parsed but never read.

- **DRY PID methods** — Extracted `_send_pid()` helper. `set_pid_param()` and
  `set_yaw_pid_param()` were identical except for function code. PID validation
  now raises `ValueError` instead of silent `print()+return`.

- **Use _send_command in set_car_motion** — Was duplicating packet building logic
  (header/checksum/write). Now delegates to `_send_command()`.

- **Fix constructor default** — `car_type=1` changed to `car_type=CARTYPE_ORBIBOT` (0x07).

- **Clean up print() statements** — Moved informational prints behind `debug` flag,
  removed debug-only prints from public methods.

- **Comment cleanup** — Rewrote file header, replaced obvious comments with docstrings,
  added units to getter methods.

### Improvements

- **Measured real IMU noise covariance** (`hardware_params.yaml`)
  Replaced hardcoded guesses (accel=0.01, gyro=0.0025) with actual measured values
  from 212 stationary samples. Previous values were ~100× too high for accel.
  Per-axis: accel X=0.000081, Y=0.000053, Z=0.000041; gyro X=0.000001, Y=0.000026, Z=0.000001.

- **Per-axis IMU covariance** (`hardware_node.py`, `hardware_params.yaml`)
  Changed from single isotropic covariance (same value all axes) to per-axis diagonal
  covariance for both accel and gyro. Config params renamed:
  `linear_acceleration_covariance` → `accel_covariance_x/y/z`,
  `angular_velocity_covariance` → `gyro_covariance_x/y/z`.
  Run `ros2 run orbibot_localization measure_imu_noise` to get actual measured values.

- **Deprecated `/orbibot/calibrate_imu` service** (`hardware_node.py`)
  Service was sending (0,0,0) to firmware which is a no-op. Now returns deprecation
  warning pointing to `ros2 run orbibot_localization calibrate_magnetometer`.
  Mag correction is Python-side only (hardware_params.yaml).

- **Clarified mag calibration architecture** (`hardware_params.yaml`)
  Added comments documenting that firmware 3x3 soft-iron matrix is NOT activated and
  all correction happens in Python `_publish_mag()`.

### Documentation

- **IMU topic architecture documented** (`README.md`)
  Added "IMU Topic Architecture" section clarifying all 4 IMU topics:
  `/imu/data` (debugging only), `/imu/data_raw` (Madgwick input),
  `/imu/mag` (Madgwick input), `/imu/data_filtered` (EKF input).
  Documents that Python-side mag correction is the active path and
  firmware 3x3 soft-iron matrix is not activated in normal operation.

## [Previous] — 2026-03-22

### Bug Fixes

- **HW-BUG-1 — `set_pid_param()` / `set_yaw_pid_param()` length byte now dynamic** (`rosmaster_driver.py`)
  Both methods previously hardcoded `0x0A` as the packet length byte before appending data
  bytes, meaning the length field was set before the packet was fully constructed. Fixed to
  use `cmd[2] = len(cmd) - 1` after building the full payload (matching the pattern used
  correctly by `set_car_motion()`). Prevents firmware packet mis-parse if the structure ever
  changes.

- **HW-BUG-2 — Yaw PID save rate limiter used correct key** (`hardware_node.py`)
  `_yaw_pid_save_callback()` was checking `'_last_yaw_pid_update'` (the temporary update
  key) instead of `'_last_yaw_pid_save_update'`. This caused a yaw PID save request to be
  silently dropped if a temporary yaw PID update was received within the rate-limit window.

- **HW-ISSUE-1 — Race condition in command timeout stop eliminated** (`hardware_node.py`)
  The `_timeout_stop_sent` flag check was split across two lock releases — `_cmd_time_lock`
  and `_state_lock` — allowing concurrent callbacks to both see `_timeout_stop_sent=False`
  and both send a stop command. Refactored so `cmd_age` measurement, `motors_enabled` read,
  and `_timeout_stop_sent` set all occur within a single `_cmd_time_lock` region.

- **HW-ISSUE-3 — `set_beep()` raises `ValueError` on invalid input** (`rosmaster_driver.py`)
  Previously used `print()` for the negative-input error, which is invisible in ROS launch
  logs and provides no feedback to the caller. Now raises `ValueError` so the hardware node
  callback can log it via `self.get_logger()`.

- **HW-ISSUE-4 — Magnetometer calibration offsets bounds-checked** (`rosmaster_driver.py`)
  `set_mag_calibration()` now validates that each offset is within `±327.67 µT` (the int16
  representable range at ×100 scaling) before calling `struct.pack('h', ...)`. Previously,
  out-of-range values caused an unhandled `struct.error` exception in the callback.

### Improvements

- **HW-GAP-3 — PID rate limit exposed as YAML parameter** (`hardware_params.yaml`, `hardware_node.py`)
  `control.pid_rate_limit` (default `0.1` s) is now declared as a ROS parameter and loaded
  at startup. Previously the 100ms rate limit was hardcoded, requiring source edits to tune.

- **HW-ISSUE-2 — `calibrate_imu` service behaviour documented** (`hardware_node.py`)
  Docstring and response message now explicitly state that this service sends offset (0,0,0)
  to the firmware (triggering the ICM-20948 to use its current reading as the reference),
  and that `bias_values` always returns `[0.0, 0.0, 0.0]` because the firmware has no
  read-back command. Users needing explicit offsets should use `/orbibot/set_mag_calibration`.

### Documentation

- **HW-DOC-1 — IMU/encoder topic rate clarified** (`README.md`)
  `/imu/data_raw`, `/imu/mag`, and `/orbibot/encoders` now document that the firmware sends
  these at ~20 Hz (one of five interleaved auto-report types), while the node re-publishes
  at the 50 Hz timer rate (most recent frame). The previous "50Hz" label was misleading.

- **HW-DOC-2 — `calibrate_imu` limitation documented** (`README.md`)
  Service description updated to note that `bias_values` always returns `[0,0,0]` and
  directs users to `/orbibot/set_mag_calibration` for explicit offset setting.

- **HW-DOC-3 — `reset_odometry` pose limitation documented** (`README.md`)
  Service description updated to note that the `reset_pose` field is not supported and the
  firmware always resets to `(0,0,0)`.

- **HW-GAP-3 — `pid_rate_limit` added to README parameter table** (`README.md`)
  New `control.pid_rate_limit` parameter documented with default value and description.

---

## [Initial] — prior to 2026-03-22

- Initial production version (see git log for full history)
