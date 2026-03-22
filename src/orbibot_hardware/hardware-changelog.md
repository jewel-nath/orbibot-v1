# Hardware Node Changelog

## [Unreleased] — 2026-03-22

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
