# Firmware Changelog

## [Unreleased] — 2026-04-28

### Bug Fixes

- **`FUNC_SET_MAG_CAL` state-byte gate** (`protocol.c`, `rosmaster_driver.py`,
  `hardware_node.py`) — DD-11
  Wire-format extended from 6 to 7 bytes: `[ox_lo][ox_hi][oy_lo][oy_hi][oz_lo][oz_hi][state]`,
  matching the SAVE_VERIFY convention already used by `FUNC_SET_MOTOR_PID`
  and `FUNC_SET_YAW_PID`. The handler now persists to flash only when
  `state == 0x5F`; otherwise the calibration update is RAM-only. Prior
  versions wrote flash unconditionally — a streaming calibration routine
  could plausibly burn 30+ erase cycles per session.
  - `protocol_min_rx_len(FUNC_SET_MAG_CAL)` bumped 11 → 12 (the dispatcher
    rejects legacy 6-byte payloads with `g_unknown_cmd_count++`).
  - Python driver gained `save: bool = False` parameter.
  - `/orbibot/set_mag_calibration` ROS 2 service still defaults to
    persist-on-call (`save=True` from the callback) so external behaviour
    is unchanged.
  - New regression test: `tests/test_mag_cal_gate.py`.

  **Compat note:** an old (pre-this-commit) Python driver paired with
  this firmware will fail mag calibration silently — flash & driver must
  ship together.

- **Critical-battery alarm priority over host BEEP(0)** (`protocol.c`) — DD-2
  When battery falls below `BATTERY_VOLTAGE_CRITICAL` (10.5 V) MonitorTask
  drives a continuous alarm + lockout. The `case FUNC_BEEP:` handler used to
  call `BUZZER_OFF()` unconditionally on `on_time == 0`, so any host (including
  `ros2 topic pub /orbibot/beep ... 0`) could silence the alarm even though
  motor lockout remained active — robot appears mute & dead. Fix: gate the
  off-path on `!control_get_battery_lockout()`. Lockout itself was always
  preserved; this restores the audible cue.

- **`protocol_start_double_beep()` write atomicity** (`protocol.c`) — DD-3
  `g_double_beep_state` and `g_double_beep_phase_tick` are written by
  MonitorTask (priority 5) and read by CommTask (priority 7) at 1 ms cadence
  via `protocol_update_buzzer()`. Without atomicity, CommTask could observe
  state=ON1 paired with the previous double-beep's stale phase_tick — fires
  `elapsed_ms ≥ 200` immediately and silences the buzzer. User would hear a
  click instead of the intended 200 ms double-beep at the moment battery
  first crosses the LOW threshold. Fix: wrap the pair in
  `taskENTER_CRITICAL/EXIT_CRITICAL`.

- **`mag_cal` cross-task struct race** (`imu_driver.c`) — DD-5
  `imu_set_mag_calibration()` runs in CommTask (priority 7) and copies a
  52-byte struct into `mag_cal`. `imu_read_both()` runs in `task_imu`
  (priority 8) at 50 Hz and uses the same struct. Higher-priority `task_imu`
  could preempt mid-copy and observe a torn snapshot of hard-iron offsets +
  soft-iron matrix, producing one bad mag-corrected sample (sub-degree yaw
  glitch — attenuated heavily by the gyro-dominated complementary filter
  but cleanly avoidable). Fix: writer wraps the copy in critical section;
  reader takes a local snapshot under critical section then runs the FP
  math unblocked, keeping the lock window to a few µs.

- **Protocol command-handler payload-length validation** (`protocol.c`) — DD-1
  Prior dispatcher accepted any checksum-valid 5-byte packet `[HEAD, 0xFC,
  LEN=3, FUNC, CKSUM]` and dispatched to handlers that read past the actual
  payload into stale RAM. Live test (`tests/test_malformed_packets.py`)
  confirmed worst-case behaviour:
  - Truncated `FUNC_MOTION (0x12)` → robot commanded at vx ≈ 1029 mm/s
    (saturated speed) from stale RAM.
  - Truncated `FUNC_SET_MOTOR_PID (0x13)` → spurious motion (vx ≈ 993 mm/s).
  - Truncated `FUNC_SET_MAG_CAL (0x16)` → unconditional `flash_storage_save()`
    with garbage hard-iron offsets, blocking long enough to miss watchdog
    feeding → IWDG reset at 5 s.

  Fix: added file-local `protocol_min_rx_len(func_code)` lookup + a single
  length gate at the top of `protocol_parse_command()`. Truncated packets
  are now rejected, increment `g_unknown_cmd_count`, and never reach the
  handler. Re-running the test post-fix shows all five at-risk function
  codes silently dropped, no rogue motion, no stream interruption. See
  `test-report.md` §9.1 for measurements.

## [Unreleased] — 2026-04-19

### Bug Fixes

- **Contract: direct `FUNC_VERSION` (0x51)** (`protocol.c`)
  `rosmaster_driver.request_firmware_version()` sends `0x51` as the function
  code directly, but the firmware dispatch switch only had the legacy
  `FUNC_REQUEST_DATA (0x50)` + sub-byte `0x51` path. Direct `0x51` fell
  through to `default` and bumped `g_unknown_cmd_count` silently — the
  `/orbibot/get_firmware_version` service therefore always returned
  `"unknown"`. Added a `case FUNC_VERSION:` that replies with `[major, minor]`.
  Legacy path retained for protocol compatibility. Verified live on 2026-04-19.

### Refactoring / Dead-code Removal

- **Unused circular RX buffer** (`hal_usart.c`, `hal_usart.h`)
  Removed `rx_buffer[256]`, `rx_head`, `rx_tail`, the ISR circular-buffer
  write branch, and the four unused read/flush APIs (`hal_usart_available`,
  `hal_usart_read_byte`, `hal_usart_read_bytes`, `hal_usart_flush_rx`).
  Saves 256 B RAM plus one store per RX byte in the ISR. Also dropped
  `SERIAL_RX_BUFFER_SIZE` / `SERIAL_TX_BUFFER_SIZE` macros from
  `orbibot_config.h` (no longer referenced anywhere).

- **Dead buzzer wrappers** (`hal_gpio.c`, `hal_gpio.h`)
  Removed `hal_gpio_set_buzzer()` (callers already use `BUZZER_ON/OFF` macros)
  and `hal_gpio_beep()` (no callers; non-blocking audio lives in
  `protocol_start_double_beep()`).

- **Dead RX counter** (`protocol.c`)
  Removed `g_rx_byte_count` — incremented on every RX byte but never read.
  Also removed the stale `// FUNC_SET_MOTOR_PID_MULTILEVEL removed` comment.

- **Dead `AUTO_SEND_TIMEOUT` macro** (`protocol.h`)
  `AUTO_SEND_TIMEOUT` had no callers; the real cycle value lives as
  `AUTO_SEND_CYCLE` inside `task_communication.c`. Replaced with a pointer
  comment to avoid future confusion.

- **Dead inline wrappers** (`protocol.h`)
  Removed `protocol_clear_command_flag()`, `protocol_enable_auto_report()`,
  `protocol_disable_auto_report()` — three `static inline` helpers with no
  callers. Kept `protocol_is_command_ready()` and
  `protocol_is_auto_report_enabled()` which are used in `task_communication.c`.

- **Unimplemented FUNC codes** (`protocol.h`)
  Moved `FUNC_MOTOR (0x10)`, `FUNC_CAR_RUN (0x11)`, `FUNC_NOW_YAW (0x52)`,
  `FUNC_RESET_FLASH (0xA0)`, `FUNC_TEST_MODE (0xA1)`, `FUNC_TEST_CLEAR_YAW
  (0xA2)` from the active `#define` section into the existing
  "Reserved / not implemented" comment block, so readers aren't misled
  about what the firmware actually supports.

### Configuration

- **OLED display disabled by default** (`orbibot_config.h`)
  Set `ENABLE_OLED_DISPLAY = 0`. Most OrbiBot builds don't have a physical
  SSD1306 soldered; the driver costs ~3 KB flash including the font table.
  Enable explicitly (`=1`) on boards that have the display fitted.

- **Battery threshold comment fix** (`orbibot_config.h`)
  Docstring block said "Low voltage: 11.6 V, Critical: 10.0 V" but the
  actual `#define`s were `11.0f` and `10.5f` (which correctly match
  `hardware_params.yaml`). Rewrote the comment to reflect real values and
  reminded maintainers that the firmware and ROS 2 YAML must stay in sync.

- **Watchdog calls gated on `ENABLE_WATCHDOG`** (`main.c`, `task_monitoring.c`)
  `hal_watchdog_feed()` was called unconditionally but `hal_watchdog_init()`
  was under `#if ENABLE_WATCHDOG`. Now both wrapped consistently so an
  `ENABLE_WATCHDOG=0` development build has no IWDG code path at all.

### Documentation

- **Auto-report rate / task priority corrections** (`firmware-architecture.md`,
  `src/tasks/task_communication.c`, `src/main.c`)
  Architecture doc and several docstrings claimed "20 Hz each, 50 ms cycle"
  and `CommTask priority 9`. Actual code does 50 Hz per type, 20 ms cycle,
  priority 7. Corrected all three. Also refreshed the function-code table
  to show both the direct `0x51` and legacy `0x50+0x51` version paths.

### Live Verification (2026-04-19)

All of the above was flashed to the real STM32 on the robot and exercised
with wheels elevated. Contract fix returns `major=2, minor=0`; all five
auto-report types stream at 54 Hz each (270 pkt/s aggregate); mecanum
forward/backward/lateral/rotate sign patterns match the documented inverse
kinematics; command timeout auto-stops motors at t ≈ 2.12 s; buzzer works;
unknown function code 0x77 is silently dropped without stalling the stream.
See `test-report.md` for the full snapshot.

Hardware observation (not a firmware defect): **M4 (Back-Right)** reports
~12–15 % fewer encoder ticks than M1–M3 across every motion type. PID
compensates so chassis velocity is still accurate, but the per-wheel count
mismatch suggests extra friction on the M4 drivetrain. Run
`test_motor_max_speed.py` per-wheel when convenient.

---

## [2.0.2] — 2026-03-25

### Refactoring

- **Remove duplicate FreeRTOS sources** (`lib/src/`)
  Deleted `lib/src/` (exact copy of `lib/FreeRTOS/src/`, not in build filter).
  Removed stale `lib/FreeRTOS/inc/FreeRTOSConfig.h` (outdated copy of `include/FreeRTOSConfig.h`).

- **Remove unused code**
  Removed: `hal_gpio_set_motor_direction/enable` (empty stubs), `dma_tx_busy` (set never read),
  `protocol_get_rx_count` (never called), `pid_get_gains_for_speed` + `pid_multilevel_t` (multi-level
  PID removed from protocol), `ENCODER_EDGES_PER_REV` alias, `ENCODER_TO_MPS_FACTOR` (unused).

- **Fix hal_i2c.c pin mismatch** — was using PB10/PB11, config defines PA2/PA3 for OLED.
  Now references `OLED_SCL_PIN/PORT` and `OLED_SDA_PIN/PORT` from `orbibot_config.h`.

- **Deduplicate encoder timer array** (`hal_timer.c`)
  Extracted `encoder_tim[4]` to file-scope constant (was duplicated in 3 functions).
  Removed redundant `TIM_SetCounter(TIMx, 0)` before `TIMx->CNT = ENCODER_MIDPOINT`.

- **Use config constants** — `hal_timer.c` references `MOTOR_MAX_PULSE` from config instead of
  local `MOTOR_MAX_PWM`. `hal_usart.c` references `SERIAL_RX_BUFFER_SIZE` from config.

- **Fix docblocks** — removed duplicate line in `hal_adc.c`, orphaned docblock in `main.c`.
  Updated OLED display strings from "v1.0" to "v2.0".

- **Comment cleanup** — removed obvious/redundant comments across HAL and task files.
  Focused on "why" (hardware quirks, safety) not "what" (obvious code).

---

## [2.0.1] — 2026-03-25

### Bug Fixes

- **FW-BUG-2 — Accelerometer Z scale factor** (`imu_driver.c`)
  ICM-20948 on this hardware produces 25644 counts/g instead of nominal 16384.
  Applied empirical scale: `accel_scale = 9.80665f / 25644.0f`. Error reduced to 0.09%.

- **FW-BUG-3 — IWDG reset loop on fast-LSI hardware** (`main.c`)
  STM32F103 LSI tolerance (30-60 kHz) can shrink watchdog timeout below startup duration.
  Added `hal_watchdog_feed()` before `vTaskStartScheduler()` to reset the 5s window.

- **FW-BUG-4 — Checksum mismatch rejected all commands** (`protocol.c`)
  `protocol_calculate_checksum()` summed from index 1 (including Device_ID=0xFC), but
  host sums from index 2 (Length onward). Changed loop start from `i = 1` to `i = 2`.

- **FW-BUG-5 — Encoder direction M2/M4 inverted** (`encoder_driver.c`)
  `encoder_direction[4]` was `{-1, -1, 1, 1}` — M2 and M4 had wrong signs, causing
  PID runaway (6x overspeed). Corrected to `{-1, 1, 1, -1}`.

### Improvements

- **Accelerometer X/Y bias calibration at startup** (`imu_driver.c`)
  `imu_calibrate()` now calibrates both gyro and accel offsets from 1000 stationary samples.
  Accel Z intentionally not corrected (Madgwick needs gravity vector).

- **Startup IMU noise variance** (`imu_driver.c`)
  Per-axis accel/gyro variance computed via Welford's algorithm during calibration.
  Exposed via `imu_get_noise_variance()` for ROS 2 Imu covariance.

- **Encoder anomaly detection** (`task_control.c`)
  Readings beyond `MAX_WHEEL_SPEED_MMS` (3500 mm/s) discarded and replaced with last valid.
  Prevents PID overshoot from EMI spikes.

- **Vy double negation eliminated** (`protocol.c`, `mecanum_kinematics.c`)
  Removed duplicate Vy negation in protocol and kinematics. ROS frame convention
  (positive = left) now used consistently throughout the control stack.

- **Velocity ramp renamed** (`orbibot_config.h`)
  `MOTOR_SPEED_RAMP_MMS` → `MOTOR_DECEL_RAMP_MMS` (only applies during deceleration).

- **IMU init failure halts boot** (`main.c`)
  Previously continued with garbage SPI data. Now halts and waits for watchdog reset.

- **Battery voltage uint8 overflow guard** (`protocol.c`)
  Saturate to 255 before uint8 cast to prevent float rounding overflow.

### Documentation

- **PID tuning procedure** added to `README.md`

---

## [2.0.0] — 2026-03-15

- Initial production release (see git log for full history)
