# orbibot_hardware — Changelog

**Audited:** 2026-02-23
**Files reviewed:** `rosmaster_driver.py`, `hardware_node.py`, `system_monitor.py`, `hardware_params.yaml`, `hardware.launch.py`, `README.md`
**References:** `rosmasterX3.md`, `lgdxrobot2.md`, upstream `Rosmaster_Lib.py`

---

## Progress Legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

---

## Architecture Review

The 3-file structure is sound and well-separated:
- `rosmaster_driver.py` — serial protocol layer (Rosmaster class, no ROS dependency)
- `hardware_node.py` — ROS 2 node bridging driver ↔ topics/services
- `system_monitor.py` — separate concern: host CPU/RAM/temp monitoring

No file splitting or renaming needed. The split maps cleanly to responsibilities.

> **Note on car_type:** OrbiBot firmware does not branch on car_type — single mecanum
> configuration only. The byte is part of the MOTION packet format and must be present for
> correct packet length. Q3 changes literal `7` to named constant `CARTYPE_ORBIBOT`.

---

## Issues

### Bugs

**BUG-1: `_sensor_callback` holds `_cmd_time_lock` while calling `set_car_motion`** (hardware_node.py)
- Timeout-stop path runs inside `with self._cmd_time_lock:`, then calls `set_car_motion(0,0,0)`.
- `set_car_motion` sleeps 2ms — `_cmd_time_lock` is held the entire time.
- Any `/cmd_vel` arriving in those 2ms is blocked.
- Fix: move `set_car_motion` call to after the lock releases.
- [x] Fixed

**BUG-2: Serial reconnect doesn't restore auto-report state** (rosmaster_driver.py)
- After `_reconnect_serial()` succeeds, no `set_auto_report_state(True)` is re-sent.
- If firmware rebooted (typical disconnect cause), it goes silent.
- Fix: add `_auto_report_enabled` flag; re-send `set_auto_report_state(True)` after successful reconnect.
- [x] Fixed

### Code Quality

**Q1: `_limit_motor_value` is dead code** (rosmaster_driver.py)
- Never called — `set_motor()` that used it was removed when raw motor control was pruned.
- [x] Fixed — removed

**Q2: No `close()` method on `Rosmaster` class** (rosmaster_driver.py)
- `__del__` is unreliable in Python. No explicit shutdown path.
- Fix: add `close()` that stops receive thread and closes serial; call it from hardware_node cleanup.
- [x] Fixed

**Q3: Magic number `car_type=7` in hardware_node** (hardware_node.py)
- Uses raw integer `7`; `rosmaster_driver.CARTYPE_ORBIBOT = 0x07` exists.
- Firmware doesn't branch on car_type, but named constant is clearer and more maintainable.
- Fix: use `rosmaster_driver.CARTYPE_ORBIBOT`.
- [x] Fixed

### Configuration

**C1: `set_auto_report_state(True, forever=True)` on every startup** (hardware_node.py)
- Writes to firmware flash on every node startup. Flash has limited write endurance.
- OrbiBot firmware enables auto-report by default (RTOS task always active).
- Fix: use `forever=False`.
- [x] Fixed

**C2: `covariance_decay` parameter missing from `hardware_params.yaml`**
- Declared in code (`default_value=0.99`) but absent from yaml.
- Fix: add `covariance_decay: 0.99` under `odometry:` in hardware_params.yaml.
- [x] Fixed

### Naming Convention

**N1: System monitor topic violates `/orbibot/` prefix convention** (system_monitor.py + orbibot_webgui)
- Publishes to `/system_status_enriched`. Convention: OrbiBot-specific topics use `/orbibot/` prefix.
- Fix: rename to `/orbibot/system_status_enriched` in system_monitor.py and all webgui references
  (useSystemStatus.ts, demo-robot.js, README.md).
- [x] Fixed

---

## Documentation Fixes (Phase 2.3 — README.md)

- [x] Fix wrong msg type for `/orbibot/pid_save` (was `std_msgs/Bool`, actually `Float32MultiArray`)
- [x] Add `/orbibot/pid_multilevel` subscription (in code but missing from README)
- [x] Fix `/odom` publish rate (was 20Hz; firmware sends at 25Hz → "up to 25Hz")
- [x] Add `/imu/data_raw` and `/imu/mag` to Publications list
- [x] Add QoS profile table for all topics
- [x] Add debug command examples
- [x] Update system_monitor topic to `/orbibot/system_status_enriched`
