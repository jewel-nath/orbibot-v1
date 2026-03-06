# orbibot_hardware — Changelog

**Audited:** 2026-03-04 (Deep Analysis)  
**Phase 3 fixes:** 2026-03-06  
**Files reviewed:** `rosmaster_driver.py`, `hardware_node.py`, `system_monitor.py`, `hardware_params.yaml`, `hardware.launch.py`, `setup.py`, `package.xml`  
**References:** Firmware README, firmware protocol spec, `hardware-issue.md`

---

## Phase 3 — Fixes Applied (2026-03-06)

| ID | Status |
|----|--------|
| BUG-3 | [x] Done — `set_car_motion(0,0,0)` moved outside `_state_lock` in `_motor_enable_callback` |
| BUG-4 | [x] Done — `reset_odometry` uses `_send_command` (length = len(cmd)-1) |
| BUG-5 / Q6 | [x] Done — `clear_auto_report_data()` removed (dead code, data race) |
| Q4 | [x] Done — Single sensor fetch per cycle (R1) |
| Q7 | [x] Done — Legacy `__main__` block removed from rosmaster_driver |
| Q8 | [x] Done — MPU9250 constants and parsing branch removed (ICM-20948 only) |
| Q9 | [x] Done — Unused FUNC_* and CARTYPE_* constants removed |
| Q10 | [x] Done — `_request_data()` removed |
| Q11 | [x] Done — Version fields and `get_version()` removed |
| Q12 | [x] Done — `set_mag_calibration` uses `FUNC_SET_MAG_CAL` |
| Q13 | [x] Done — `_send_command()` helper; beep, auto_report, mag_cal, reset_flash, reset_odom use it |
| Q14 | [x] Done — `class Rosmaster:` (Python 3 style) |
| R1 | [x] Done — Single fetch in `_sensor_callback`, pass to all `_publish_*` |
| R2 | [x] Done — `robot.wheel_radius`, `robot.encoder_edges_per_rev` in YAML and node |
| R4 | [x] Done — `imu.*_covariance` in YAML and publish methods |
| R5 | [x] Done — `_send_command(func_code, data_bytes)` in rosmaster_driver |
| S1 | [x] Done — `hardware.data_timeout`; `hardware_connected` set False on data timeout |
| S2 | [x] Done — `_last_data_timestamp` in driver, checked in `_sensor_callback` |
| P1 | [x] Done — system_monitor: seed `cpu_percent(interval=0.1)` once, then `interval=None` |
| D1 | [x] Done — Comment clarified: "Driver version / Yahboom protocol compatibility (V3.3.9)" |

---

## Progress Legend
- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

---

## Phase 1 — Previously Fixed (2026-02-23)

All items from the original audit have been resolved:

| ID | Type | Description | Status |
|----|------|-------------|--------|
| BUG-1 | Bug | `_sensor_callback` held `_cmd_time_lock` during `set_car_motion` (2ms serial sleep blocked `/cmd_vel`) | [x] Fixed |
| BUG-2 | Bug | Serial reconnect didn't restore auto-report state | [x] Fixed |
| Q1 | Quality | `_limit_motor_value` dead code | [x] Removed |
| Q2 | Quality | No `close()` method on Rosmaster class | [x] Added |
| Q3 | Quality | Magic number `car_type=7` | [x] Uses `CARTYPE_ORBIBOT` |
| C1 | Config | `set_auto_report_state(True, forever=True)` wrote flash on every startup | [x] Uses `forever=False` |
| C2 | Config | `covariance_decay` missing from YAML | [x] Added |
| N1 | Naming | System monitor topic violated `/orbibot/` prefix | [x] Fixed |
| HW-001 | Issue | Topic naming verified correct | [x] |
| HW-002 | Issue | `psutil` dependency added to `package.xml` | [x] |
| HW-005 | Issue | PID rate limiting added (max 10Hz) | [x] |

---

## Phase 2 — Deep Code Analysis (2026-03-04)

### Bugs

**BUG-3: `_motor_enable_callback` holds `_state_lock` during serial write** (hardware_node.py:821)
- Identical antipattern to BUG-1 (which was fixed in `_sensor_callback`).
- When disabling motors, `self.bot.set_car_motion(0, 0, 0)` is called INSIDE `with self._state_lock:`.
- `set_car_motion()` contains `time.sleep(0.002)` — lock is held ~2ms.
- Any concurrent callback reading `motors_enabled` or `emergency_stop` (50Hz sensor, 10Hz safety) is blocked.
- Fix: move `set_car_motion(0, 0, 0)` outside the `_state_lock` block, same pattern as BUG-1 fix.
- [x] Done (Phase 3)

**BUG-4: `reset_odometry()` sends wrong packet length byte** (rosmaster_driver.py:587)
- Current: `cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x02, FUNC_RESET_ODOM]`
- Length byte `0x02` doesn't match the protocol convention used by ALL other commands.
- Convention: `LEN = len(cmd_before_checksum) - 1`. For 4-element cmd, that's `3 = 0x03`.
- Comparison with other commands that follow the convention:
  - `set_beep`: 6 elements → `LEN = 0x05` ✓
  - `set_auto_report`: 6 elements → `LEN = 0x05` ✓
  - `set_car_motion`: dynamic `cmd[2] = len(cmd) - 1` ✓
  - `set_pid_param`: 11 elements → `LEN = 0x0A` ✓
  - `reset_flash_value`: 5 elements → `LEN = 0x04` ✓
  - `reset_odometry`: 4 elements → `LEN = 0x02` ✗ (should be `0x03`)
- Impact: Firmware skips checksum validation for this command. Works because the function code
  alone identifies the command and there's no data to corrupt, but technically violates protocol.
- Fix: change `0x02` to `0x03`, or use dynamic `cmd[2] = len(cmd) - 1` pattern.
- [x] Done (Phase 3 — _send_command)

**BUG-5: `clear_auto_report_data()` missing `_data_lock`** (rosmaster_driver.py:599-605)
- Writes `_vx`, `_vy`, `_vz`, `_ax`, etc. without acquiring `_data_lock`.
- The receive thread concurrently writes these same fields inside `_data_lock`.
- This is a data race — partial writes can produce inconsistent readings.
- Also dead code: never called from `hardware_node.py`.
- Fix: either remove entirely (dead code) or add `with self._data_lock:` wrapper.
- [x] Done (Phase 3 — removed)

---

### Code Quality

**Q4: Redundant sensor data fetches per cycle** (hardware_node.py:476-484)
- `_sensor_callback` calls `_publish_imu()`, `_publish_imu_raw()`, `_publish_mag()` independently.
- `_publish_imu()` fetches: `get_accelerometer_data()`, `get_gyroscope_data()`, `get_imu_attitude_data()`.
- `_publish_imu_raw()` fetches: `get_accelerometer_data()`, `get_gyroscope_data()` — duplicates!
- Each getter acquires `_data_lock`. At 50Hz that's ~10 lock acquisitions/cycle instead of ~2.
- Fix: fetch all sensor data once at the top of `_sensor_callback` and pass to publish methods.
- [x] Done (Phase 3 — R1)

**Q5: Duplicate rate-limiting boilerplate across 4 PID callbacks** (hardware_node.py:341-453)
- `_pid_callback`, `_yaw_pid_callback`, `_pid_multilevel_callback`, `_pid_save_callback` each repeat:
  ```python
  current_time = time.time()
  if current_time - self._last_*_update < self._pid_rate_limit:
      return
  self._last_*_update = current_time
  ```
- Fix: extract to a `_rate_limit(attr_name)` helper or use a decorator.
- [ ] Not started

**Q6: `clear_auto_report_data()` is dead code** (rosmaster_driver.py:599-605)
- Never called from `hardware_node.py` or any other consumer.
- If needed in the future, needs `_data_lock` (see BUG-5). If not needed, remove.
- [x] Done (Phase 3 — removed)

**Q7: `__main__` block is legacy Windows test code** (rosmaster_driver.py:658-694)
- Scans Windows COM ports (`COM1` through `COM256`) — OrbiBot runs on RPi Linux.
- Uses bare `except:` which catches `SystemExit` and `KeyboardInterrupt`.
- Not useful for production; should be removed or moved to `tests/`.
- [x] Done (Phase 3 — removed)

**Q8: MPU9250 constants and handler are dead code** (rosmaster_driver.py:51-54, 191-203)
- OrbiBot uses ICM-20948 exclusively. Firmware only sends `FUNC_REPORT_ICM_RAW` (0x0E).
- `MPU9250_GYRO_RATIO`, `MPU9250_ACCEL_RATIO`, `MPU9250_MAG_RATIO` and the entire
  `FUNC_REPORT_MPU_RAW` parsing branch are never executed.
- Confusing for maintainers who might wonder which IMU is active.
- Fix: remove MPU9250 constants and parsing branch. Add comment noting ICM-20948 only.
- [x] Done (Phase 3)

**Q9: Unused protocol constants** (rosmaster_driver.py:30-48)
- Function codes never used by any caller:
  - `FUNC_MOTOR` (0x10) — raw motor control, pruned
  - `FUNC_CAR_RUN` (0x11) — car_run, pruned
  - `FUNC_SET_CAR_TYPE` (0x17) — car type select, not needed
  - `FUNC_RESET_STATE` (0x0F) — protocol reset, never called
  - `FUNC_REQUEST_DATA` (0x50) — polling mode, not used (auto-report instead)
- Car type constants never used by any caller:
  - `CARTYPE_X3`, `CARTYPE_X3_PLUS`, `CARTYPE_X1`, `CARTYPE_R2`
- Fix: remove unused constants. Keep only what OrbiBot actually uses.
- [x] Done (Phase 3)

**Q10: `_request_data()` method is dead code** (rosmaster_driver.py:337-345)
- Auto-report mechanism means we never poll for data. Method is never called.
- Fix: remove.
- [x] Done (Phase 3)

**Q11: Version fields never used** (rosmaster_driver.py:113-115, 249-255, 654-655)
- `_version_H`, `_version_L`, `_version`, `get_version()` exist but are never called from
  `hardware_node.py`. The firmware version query (`FUNC_VERSION`) is never sent.
- Fix: either expose firmware version in system status (useful!) or remove dead code.
- [x] Done (Phase 3 — removed)

**Q12: `set_mag_calibration` uses literal instead of constant** (rosmaster_driver.py:553)
- `cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x09, 0x16]` — uses `0x16` literal.
- `FUNC_SET_MAG_CAL = 0x16` is already defined at line 36.
- Fix: use `FUNC_SET_MAG_CAL`.
- [x] Done (Phase 3)

**Q13: Hardcoded packet length bytes are fragile** (rosmaster_driver.py)
- Most commands hardcode the length byte (e.g., `0x05`, `0x0A`, `0x1C`).
- Only `set_car_motion` uses the robust pattern: `cmd[2] = len(cmd) - 1`.
- If someone adds/removes a data byte without updating the hardcoded length, packet is malformed.
- Fix: use `cmd[2] = len(cmd) - 1` pattern in all send methods, or a `_build_packet()` helper.
- [x] Done (Phase 3 — _send_command)

**Q14: Old-style class declaration** (rosmaster_driver.py:66)
- `class Rosmaster(object):` — explicit `object` base is unnecessary in Python 3.
- Fix: `class Rosmaster:`.
- [x] Done (Phase 3)

---

### Architecture & Refactoring

**R1: Sensor data should be fetched once per cycle** (hardware_node.py:455-484)
- Currently each `_publish_*` method independently calls driver getters.
- Proposal: at the top of `_sensor_callback`, read all data into a struct/dict:
  ```python
  accel = self.bot.get_accelerometer_data()
  gyro = self.bot.get_gyroscope_data()
  attitude = self.bot.get_imu_attitude_data(to_angle=False)
  mag = self.bot.get_magnetometer_data()
  odom = self.bot.get_firmware_odometry()
  encoders = self.bot.get_motor_encoder()
  ```
  Then pass to `_publish_imu(accel, gyro, attitude)`, etc.
- Benefits: fewer lock acquisitions (~10 → ~5), consistent data across all published messages
  for the same cycle, cleaner separation between data acquisition and publishing.
- [x] Done (Phase 3)

**R2: Hardcoded robot constants should be parameters** (hardware_node.py:83-84)
- `wheel_radius = 0.05` and `encoder_edges_per_rev = 1320` are hardcoded.
- If wheel radius or encoder CPR ever changes (different wheel set, different gear ratio),
  requires code changes instead of YAML edits.
- Fix: add to `hardware_params.yaml` under `robot:` section.
- [x] Done (Phase 3)

**R3: No dynamic parameter reconfiguration** (hardware_node.py)
- All parameters are loaded once in `__init__`. ROS 2 `ros2 param set` commands have no effect
  until the node is restarted.
- Fix: add `add_on_set_parameters_callback` for runtime-tunable parameters
  (at minimum: `cmd_timeout`, `max_velocity`, `max_angular_velocity`).
- [ ] Not started

**R4: IMU covariance values are magic numbers** (hardware_node.py:523-525, 555-558)
- Accel covariance `0.01`, gyro covariance `0.0025`, orientation covariance `0.0025`
  are hardcoded in the publish methods.
- Fix: make configurable via `hardware_params.yaml` under `imu:` section, or at minimum
  define as named class constants with comments explaining their derivation.
- [x] Done (Phase 3 — imu.* in YAML)

**R5: Packet builder helper for rosmaster_driver** (rosmaster_driver.py)
- Every send method manually constructs packets: `cmd = [HEAD, DEVID, LEN, FUNC, ...]`,
  computes checksum, wraps in `_write_lock`, calls `ser.write()`, and sleeps.
- This boilerplate is repeated ~10 times and is error-prone (see BUG-4 wrong length).
- Fix: extract `_send_command(func_code, data_bytes)` method that handles:
  - Packet framing (HEAD + DEVID + LEN)
  - Dynamic length calculation
  - Checksum computation
  - Write lock + serial write
  - Post-write delay
- [x] Done (Phase 3)

**R6: Receive thread could use buffered reads** (rosmaster_driver.py:278-334)
- `_receive_data` reads one byte at a time via `self.ser.read(1)`.
- Many syscalls per packet (minimum 4 for a simple command, 20+ for encoder report).
- Fix: read available bytes into a buffer, parse from buffer. Use `self.ser.in_waiting`
  to batch reads. Significant CPU reduction on RPi at 50Hz+ data rate.
- [ ] Not started

---

### Safety & Robustness

**S1: `hardware_connected` never transitions to `False`** (hardware_node.py)
- Set to `True` once in `_initialize_hardware`. Never reverted during serial disconnect.
- The receive thread in rosmaster_driver handles reconnection internally, but the hardware node
  keeps publishing stale cached data as if the connection is healthy.
- Fix: add data freshness monitoring. If no new firmware data arrives for N seconds,
  set `hardware_connected = False` and log a warning. Re-set to `True` when data resumes.
- [x] Done (Phase 3)

**S2: Stale data published during serial disconnect** (hardware_node.py)
- Related to S1. During the reconnection window (up to 10 retries × 1s = 10s), the node
  continues calling `bot.get_*()` which return old cached values.
- EKF/SLAM consumers have no way to know the data is stale.
- Fix: add a `_last_data_timestamp` in rosmaster_driver updated on each successful parse.
  hardware_node checks freshness before publishing. Alternatively, set a "stale" flag that
  consumers can check, or stop publishing and let topic timeouts handle it.
- [x] Done (2026-03-06)

**S3: After battery emergency recovery, motors stay disabled** (hardware_node.py:804-807)
- When `critical_battery` is detected, `emergency_stop = True` and `motors_enabled = False`.
- When voltage recovers, `emergency_stop` is cleared but `motors_enabled` remains `False`.
- User must manually call `set_motor_enable` service — may not realize motors need re-enabling.
- This is arguably a safety feature (explicit re-enable after critical event), but should
  at minimum log a clear message: "Battery recovered. Motors disabled — call set_motor_enable."
- [ ] Not started — decide if this is intended behavior or should auto-recover

**S4: Motor enable on startup has no retry** (hardware.launch.py:57-67)
- `TimerAction(period=3.0)` calls `ros2 service call` once. If the hardware node hasn't
  finished initialization in 3s (e.g., serial port not ready), the service call fails silently.
- Fix: use a longer delay (5s), or implement retry logic in the launch file,
  or move the auto-enable logic into the hardware_node itself with a startup timer.
- [ ] Not started

---

### Performance

**P1: `system_monitor` blocks 100ms per cycle** (system_monitor.py:81)
- `psutil.cpu_percent(interval=0.1)` blocks the thread for 100ms on every 1Hz timer call.
- On RPi 5 with MultiThreadedExecutor this is a minor issue, but on SingleThreadedExecutor
  (which system_monitor uses) it delays all other callbacks by 100ms.
- Fix: use `psutil.cpu_percent(interval=None)` which returns instantly (percent since last call).
  Call once at startup with `interval=0.1` to seed the baseline, then `interval=None` afterward.
- [x] Done (2026-03-06)

---

### Packaging

**PKG-1: Missing `__init__.py`** (orbibot_hardware/)
- The `orbibot_hardware/` Python package directory has no `__init__.py`.
- `find_packages()` in `setup.py` requires `__init__.py` to discover the package.
- If the package builds and works on the RPi, this file must exist there — verify it's committed.
- [ ] Not started — verify on build system

**PKG-2: Missing `resource/orbibot_hardware` marker file**
- `setup.py` references `resource/orbibot_hardware` for ament index registration.
- File not found in repository — `colcon build` would fail without it.
- Same as PKG-1: verify it exists on the build system and is committed.
- [ ] Not started — verify on build system

---

### Testing

**T1: No unit tests** (test/)
- No `test/` directory. No pytest tests for:
  - Protocol parsing (`_parse_data` with various packet types)
  - Checksum computation (valid/invalid packets)
  - Covariance math (adaptive drift, decay, wraparound)
  - Parameter validation (boundary conditions)
- These can all be tested without hardware using mocked serial data.
- [ ] Not started

**T2: No launch/integration tests**
- No launch test to verify nodes start and produce expected topics.
- ROS 2 launch_testing could verify topic existence and basic message flow.
- [ ] Not started

---

### Documentation (Minor)

**D1: `# V3.3.9` comment on class is opaque** (rosmaster_driver.py:65)
- No context for what "V3.3.9" refers to (driver version? Yahboom protocol version?).
- Fix: either expand to meaningful comment or move to module docstring.
- [x] Done (2026-03-06)

---

## Recommended Priority

### Immediate (Bug fixes)
1. **BUG-3** — Lock held during serial write in `_motor_enable_callback` (copy of fixed BUG-1 pattern)
2. **BUG-4** — Wrong packet length in `reset_odometry`
3. **BUG-5** / **Q6** — Remove dead `clear_auto_report_data()` (fixes race + removes dead code)

### Short Term (Code quality + safety)
4. **R5** — Packet builder helper (prevents future BUG-4 class errors)
5. **Q13** — Dynamic length calculation for all commands
6. **R1** — Single sensor fetch per cycle (reduces lock contention at 50Hz)
7. **S1** + **S2** — Data freshness monitoring (prevents stale data during disconnect)
8. **Q4** — Deduplicate sensor fetches (part of R1)
9. **P1** — Fix blocking `cpu_percent` in system_monitor

### Medium Term (Cleanup + architecture)
10. **Q8** — Remove MPU9250 dead code
11. **Q9** + **Q10** + **Q11** — Remove unused constants and methods
12. **Q7** — Remove legacy `__main__` test block
13. **R2** — Parameterize robot constants (wheel_radius, encoder_CPR)
14. **R3** — Dynamic parameter reconfiguration callback
15. **R4** — Parameterize IMU covariance values
16. **Q12** — Use `FUNC_SET_MAG_CAL` constant
17. **Q14** — Python 3 class style
18. **Q5** — DRY the PID rate-limiting boilerplate
19. **D1** — Clarify version comment

### Long Term (Robustness + testing)
20. **S3** — Decide motor recovery behavior after battery emergency
21. **S4** — Startup motor enable retry logic
22. **R6** — Buffered serial reads for CPU reduction
23. **T1** — Unit tests for protocol parsing and covariance math
24. **T2** — Launch integration tests
25. **PKG-1** + **PKG-2** — Verify packaging files on build system

---

## Architecture Review

The 3-file structure remains sound and well-separated:
- `rosmaster_driver.py` — serial protocol layer (Rosmaster class, no ROS dependency)
- `hardware_node.py` — ROS 2 node bridging driver ↔ topics/services
- `system_monitor.py` — separate concern: host CPU/RAM/temp monitoring

No file splitting or renaming needed. The main refactoring opportunities are:
1. **Within `rosmaster_driver.py`**: extract `_send_command()` helper (R5), remove dead code (Q6-Q11),
   clean up constants (Q8-Q9)
2. **Within `hardware_node.py`**: single-fetch sensor pattern (R1/Q4), fix lock antipattern (BUG-3),
   parameterize constants (R2/R4), add freshness monitoring (S1/S2)
3. **Within `system_monitor.py`**: fix blocking CPU call (P1) — single-line change

> **Note on car_type:** OrbiBot firmware does not branch on car_type — single mecanum
> configuration only. The byte is part of the MOTION packet format and must be present for
> correct packet length. Q3 changes literal `7` to named constant `CARTYPE_ORBIBOT`.
