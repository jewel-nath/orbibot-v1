# Hardware Node Changelog

## [Unreleased] — 2026-08-04

### Investigated — HW-BUG-8 has a cause, and it is not the firmware

No code changed in this package yet; the fix is scoped and pending. What changed
is that the bug is finally characterised correctly, after two wrong attempts.

- **The board was exonerated in fifteen seconds.** `.claude/scripts/rate_decay_log.py`
  reads the ROSMaster's serial stream with no ROS stack running: **49.98 Hz on
  all five report types at 2 h 41 min of board uptime**, battery 12.5 V. Nine
  minutes earlier, at a *shorter* uptime, ROS `/imu/data_raw` had read 39.0 Hz.
  "Decays with board uptime" was therefore impossible, and the three-hour
  measurement planned to test it was cancelled before it ran.
- **The cause is `/cmd_vel` traffic.** Bisecting one launch file at a time:
  hardware alone 50.0 Hz, plus localization 50.0, plus lidar 50.0, plus
  twist_mux **37.4**. Replacing twist_mux with a bare
  `ros2 topic pub -r 20 /cmd_vel` still reproduced it at **32.4 Hz**, which
  clears twist_mux and points at this node's own subscription path.
- **The cost is in the executor, not the callback.** Per-thread CPU under 20 Hz
  of `/cmd_vel`: main/executor thread 6.0 % → **55.3 %**, serial receive thread
  **2.0 % → 2.0 %**. That is ~24.5 ms of main-thread CPU per message, with
  `motors_enabled: false`, where `_cmd_vel_callback` takes two locks and returns
  without touching the serial port. The 24.5 ms is **not yet explained** and no
  explanation is being written down until it is measured.
- **Severity raised to HIGH.** The old framing — a rate that sags on a parked
  robot — was cosmetic. The real behaviour is that odometry and IMU drop by a
  third *while the robot is being driven*, since teleop, the agent and Nav2 all
  command at ~20 Hz. Phase 4 filter tuning is blocked until this is fixed.

Fix plan, measurements and a 90-second reproduction: `hardware-issue.md`,
HW-BUG-8. Regression guard: `.claude/scripts/topic_rate_log.py`.

## [Unreleased] — 2026-08-03

### Fixed

- **`system_monitor.py` reported the WiFi card's temperature as the CPU's.**
  `get_cpu_temperature()` read `/sys/class/thermal/thermal_zone0/temp`
  unconditionally. On the Raspberry Pi 5 that zone was the CPU. On the Beelink
  SER5 Pro, which replaced it on 2026-08-03, the *only* thermal zone is
  `iwlwifi_1` — the WiFi adapter. The node would have published ~50 °C as a CPU
  temperature, and nothing downstream could have told it was the wrong chip.

  Thermal-zone ordering is not stable across machines and carries no meaning.
  The sensor is now identified **by name**, not position:

  1. `/sys/class/hwmon/*` matched against `k10temp` (AMD), `coretemp` (Intel),
     `cpu_thermal` (Pi) — first match wins
  2. `/sys/class/thermal/*` with the zone's `type` checked before its `temp`
  3. `psutil.sensors_temperatures()` as a last resort, same driver names

  Verified on the Beelink: 44.4 °C from `k10temp`/`Tctl`, and the thermal-zone
  path correctly declines the WiFi sensor rather than returning it.

  This is the failure mode `.claude/rules/docs-sync.md` is about, in code
  rather than prose — a plausible number from the wrong source is worse than
  no number, because it does not look broken.

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
