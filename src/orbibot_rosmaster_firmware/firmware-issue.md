# Firmware Issue Tracker

**Package:** `orbibot_rosmaster_firmware` (STM32F103RCT6)
**Last Updated:** 2026-04-19

This file lists **open** issues only. Fixed items live in
`firmware-changelog.md` under the version in which they were resolved.

---

## 🟠 Open issues (need hardware or further thought before fixing)

### FW-ISSUE-4: `MAX_WHEEL_SPEED_MMS` is theoretical, not measured
**Severity:** INFO · **File:** `include/orbibot_config.h`

`MAX_WHEEL_SPEED_MMS` (3500 mm/s) is 2× the theoretical per-motor max. An
overly generous anomaly-rejection threshold lets real EMI spikes through.
`lgdxrobot2` found 23 % per-motor variation, and this robot's M4 looks
~12-15 % slower than M1–M3 (see §Hardware observation below). Threshold
should be `1.5 × measured worst-case max`.

**How to measure:** Run `tests/test_motor_max_speed.py` at full PWM for each
wheel (robot elevated), record steady-state encoder velocity, pick the
largest and multiply by 1.5.

---

### FW-ISSUE-7: IMU variance never transmitted to ROS 2
**Severity:** INFO · **Files:** firmware side — `imu_driver.c`,
`protocol.c`; ROS 2 side — `hardware_node.py`, `hardware_params.yaml`

`imu_calibrate()` computes accel and gyro variance via Welford's algorithm
during boot calibration and keeps them in `accel_variance[3]` / `gyro_variance[3]`
accessible via `imu_get_noise_variance()`. But nothing reads the getter —
the ROS 2 side hardcodes the covariance diagonals from an offline
`measure_imu_noise` utility.

**Fix (requires both firmware and ROS 2 change):** Add a new outgoing
report (e.g. `0x17 REPORT_IMU_NOISE`, 12 B = 6 × int16 scaled) that the
firmware sends once after boot calibration. `hardware_node` caches it and
uses it for the `Imu` covariance matrix instead of YAML values.

---

### FW-ISSUE-8: `pid_controller_t.deadzone` field is dead
**Severity:** LOW · **Files:** `include/pid_controller.h`,
`src/control/pid_controller.c`

The struct has a `float deadzone` field; `pid_init()` sets it to `0.0f` but
`pid_calculate_incremental()` never reads it. Deadzone compensation happens
one layer up in `motor_driver.c::motor_apply_deadzone()` (adds the
`MOTOR_IGNORE_PULSE` offset to any non-zero PWM command).

**Fix:** Remove the field from `pid_controller_t` and the init assignment.
Keep `motor_apply_deadzone()` where it is. Safe — no caller sets or reads
the field.

---

### FW-ISSUE-9: `hal_i2c_init()` called even when OLED is disabled
**Severity:** LOW · **File:** `src/main.c` — `hardwareInit()`

`hardwareInit()` calls `hal_i2c_init()` inside `#if ENABLE_OLED_DISPLAY`,
so this one is actually correct on the boot path. But the `hal_i2c.c` /
`hal_ssd1306.c` / `oled_driver.c` / `oled_fonts.c` objects are still
compiled into the firmware (filtered by `-ffunction-sections --gc-sections`
at link time, which does GC them — verified by 28.7 KB flash on
`ENABLE_OLED_DISPLAY=0`). No runtime cost, but ~3 KB compile-time waste.

**Fix (optional):** Add `#if ENABLE_OLED_DISPLAY` wrappers inside the
driver/HAL source files themselves so they don't compile at all when
disabled. Or move the files into a `build_src_filter` rule in
`platformio.ini` gated on the config flag. Low priority — the linker
already does the right thing.

---

### FW-ISSUE-10: Dead public API clutters driver headers
**Severity:** INFO · **Files:** multiple header + source pairs

The following functions are part of their driver's public header but have
**zero callers** in the firmware (verified by grep). They are GC'd by the
linker (no runtime cost) but inflate the documented API surface and
make the driver harder to reason about:

| File | Dead exports |
|------|--------------|
| `imu_driver.{c,h}` | `imu_read_accel/gyro/mag/temperature`, `imu_reset`, `imu_self_test`, `imu_set_config`, `imu_get_config`, `imu_get_gyro_raw`, `imu_get_accel_raw`, `imu_get_mag_raw` (11 funcs) — superseded by `imu_read_both` + `imu_task_*` cache |
| `motor_driver.{c,h}` | `motor_stop`, `motor_stop_all` — superseded by `motor_set_speed(i, 0)` |
| `battery_monitor.{c,h}` | `battery_is_low`, `battery_is_critical` — only `battery_get_voltage()` is used |
| `encoder_driver.{c,h}` | `encoder_get_all`, `encoder_reset` (single-motor) — only `encoder_get_count`, `encoder_read_delta`, `encoder_reset_all` are used |
| `flash_storage.{c,h}` | `flash_storage_is_valid` — magic check lives inside `flash_storage_load()` |
| `hal_gpio.{c,h}` | `hal_gpio_read_key1`, `hal_gpio_set_led` (only `hal_gpio_toggle_led` is used) |
| `hal_spi.{c,h}` | `hal_spi_set_speed`, `hal_spi_write_bytes` |
| `hal_timer.{c,h}` | `hal_timer_get_encoder_count` (replaced by `hal_timer_read_encoder_delta`) |
| `hal_usart.{c,h}` | `hal_usart_send_string` |

**Fix:** Trim these in a single pass. They're safe to delete because no
code path reaches them. Leave only what is actually used plus anything
that is clearly a "future hook" (e.g. `flash_storage_is_valid` could be
useful for diagnostics). Best done as one focused refactor PR.

---

### FW-ISSUE-11: ADC resolution constant off-by-one
**Severity:** INFO (negligible, < 0.03 % error) · **Files:** `hal_adc.c`,
`battery_monitor.c`

`hal_adc.c` uses `ADC_MAX_VALUE = 4095` (correct — 12-bit ADC range is
0..4095) while `battery_monitor.c` uses `ADC_MAX_VALUE = 4096.0f`. A
voltage converted with the latter is ~0.024 % low (12.5 V reads 12.497 V).
Well below sensor noise; the EMA filter hides it entirely. Listed for
consistency hygiene.

**Fix:** Change `battery_monitor.c::ADC_MAX_VALUE` to `4095.0f`. Or share
one `#define` in `orbibot_config.h`.

---

## 🟡 Deferred (architectural — risky without hardware regression tests)

### TD-1: `protocol.c` is ~800 lines, mixes concerns  `[DEFERRED]`
Split into `protocol_rx.c` (state machine + parse), `protocol_tx.c`
(all `protocol_send_*` reporters), `protocol_cmd.c` (handlers),
`protocol_buzzer.c` (beep state machine). Kept in one file for now
because splitting risks subtle static-variable-visibility regressions
that need live hardware to catch.

### TD-2: `imu_driver.c` is ~1000 lines, mixes concerns  `[DEFERRED]`
Split into core (`imu_driver.c`), calibration + variance (`imu_calibration.c`),
and AK09916 I²C-master (`imu_mag.c`).

### TD-3: `task_control.c` mixes control, ramp, yaw, odometry  `[DEFERRED]`
Extract `yaw_controller.c` (yaw PID + activation logic). Keep velocity
ramp inline (too small to split).

---

## 💡 Improvement Ideas (future work)

- **DMA RX** — replace byte-ISR with DMA + idle-line detection (saves ~11.5k ints/s).
- **Zero-copy protocol TX** — build packets directly in the DMA buffer.
- **Diagnostics status packet** — a periodic 0x? report containing
  `g_rx_drop_count`, `g_unknown_cmd_count`, `usart_errors`, uptime.
  Currently these counters are incremented but never surfaced.
- **Unified `motor.h`** — `motor_set_speed / motor_read_speed / motor_stop`
  hiding the HAL timer / driver split.
- **Configurable auto-report** — runtime-selectable which of the 5
  report types stream, and at what rate, to save bandwidth for IMU-only
  or encoder-only use cases.
- **CAN passthrough** — SN65HVD230 is already on the board; adding CAN
  RX/TX would enable external sensor boards.

---

## Hardware observation (2026-04-19, not a firmware defect)

**M4 (Back-Right)** reports ~12–15 % fewer encoder ticks than M1–M3 across
every motion type (forward, backward, lateral, rotate). Sign is correct
and chassis velocity still tracks the command (PID compensates by giving
M4 more PWM), but the per-wheel count mismatch suggests extra friction
somewhere on the M4 drivetrain. When convenient, run
`tests/test_motor_max_speed.py` per-wheel at full PWM; if M4 > 10 % below
M1–M3 at no-load, inspect bearings / gear mesh / wheel alignment.

---

## See also
- `firmware-changelog.md` — fixed items and full change history
- `test-report.md` — live hardware verification snapshot
