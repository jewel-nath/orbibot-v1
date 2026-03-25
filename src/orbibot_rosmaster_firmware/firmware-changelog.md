# Firmware Changelog

## [Unreleased] — 2026-03-25

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
