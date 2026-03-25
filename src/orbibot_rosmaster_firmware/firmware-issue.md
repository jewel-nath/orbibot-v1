# Firmware Issue Tracker

**Package:** `orbibot_rosmaster_firmware` (STM32F103RCT6, v2.0.1)
**Last Updated:** 2026-03-25

---

## 🔴 Open Issues

### FW-ISSUE-1: Unused circular RX buffer wastes RAM and ISR cycles
**Severity:** MEDIUM
**File:** `src/hal/hal_usart.c`

The USART1 ISR stores every received byte into both the protocol state machine AND
a 256-byte circular buffer (`rx_buffer`). The circular buffer read functions
(`hal_usart_available`, `hal_usart_read_byte`, `hal_usart_read_bytes`) are never
called by any firmware code.

**Impact:** 256 bytes wasted RAM + unnecessary ISR work on every byte (~11.5K/sec at 115200 baud).

**Fix:** Remove circular buffer writes from ISR and the unused read functions. Keep `hal_usart_flush_rx()` as a no-op or remove as well.

---

### FW-ISSUE-2: hal_gpio_beep() uses blocking busy-wait delay
**Severity:** LOW
**File:** `src/hal/hal_gpio.c`

`hal_gpio_beep()` uses a `for(volatile ...)` loop for timing. Only called during boot
(inside `#if ENABLE_BOOT_MESSAGES`), but if called after FreeRTOS starts it blocks the
calling task and starves lower-priority tasks.

**Fix:** Replace with non-blocking buzzer via `protocol_start_double_beep()` pattern, or
add a `__attribute__((deprecated))` warning.

---

### FW-ISSUE-3: hal_gpio_set_buzzer() is never called
**Severity:** LOW
**File:** `src/hal/hal_gpio.c`

Buzzer is controlled directly via `BUZZER_ON()` / `BUZZER_OFF()` macros everywhere.
The wrapper function exists but has zero callers.

**Fix:** Remove function and header declaration, or consolidate all buzzer usage through it.

---

### FW-ISSUE-4: MAX_WHEEL_SPEED_MMS is theoretical, not measured
**Severity:** INFO
**File:** `include/orbibot_config.h`

`MAX_WHEEL_SPEED_MMS` (3500 mm/s) is 2× the theoretical max from motor specs.
lgdxrobot2 found 23% variation between individual motors (10.47–12.85 rad/s).
An overly generous threshold reduces anomaly rejection effectiveness.

**Fix:** Run `test_motor_speed.py` at full PWM, measure actual per-motor max speed,
and set threshold to 1.5× measured max.

---

### FW-ISSUE-5: OLED display code compiles but is unused (~3KB flash)
**Severity:** INFO
**Files:** `oled_driver.c`, `hal_ssd1306.c`, `oled_fonts.c`, `hal_i2c.c`

`ENABLE_OLED_DISPLAY=1` in config, but the OLED is a stub on most OrbiBot builds
(no display connected). The font table alone is ~1.9KB. Total ~3KB flash for an
unused peripheral.

**Fix:** Set `ENABLE_OLED_DISPLAY=0` as default. Only enable for boards with display.

---

## 🟡 Technical Debt

### TD-1: protocol.c is too large (807 lines)
**File:** `src/communication/protocol.c`

Mixes RX state machine, command dispatch, TX reporting, PID handlers, buzzer
state machine, and odometry reporting in one file.

**Refactor:** Split into `protocol_rx.c` (state machine + parse), `protocol_tx.c`
(all `protocol_send_*` functions), `protocol_cmd.c` (command handlers).

---

### TD-2: imu_driver.c mixes concerns (~500 lines)
**File:** `src/drivers/imu_driver.c`

Init, calibration, sensor read, attitude computation, and AK09916 magnetometer
I2C master are all in one file.

**Refactor:** Extract `imu_calibration.c` (startup calibration + variance) and
`imu_mag.c` (AK09916 I2C master functions).

---

### TD-3: task_control.c mixes control, ramping, yaw, and odometry
**File:** `src/tasks/task_control.c`

The 440-line control loop handles PID control, velocity ramping, yaw drift
correction, and odometry integration in a single function.

**Refactor:** Extract `yaw_controller.c` (yaw PID + activation logic) and
keep velocity ramp inline (too small to split).

---

## 💡 Improvement Ideas

### Performance

- **DMA RX for USART1:** Replace byte-by-byte ISR with DMA RX + idle line detection.
  Eliminates ~11.5K interrupts/sec at 115200 baud.

- **Zero-copy protocol TX:** Build packets directly in DMA buffer instead of
  stack → memcpy → DMA. Saves one copy per packet (~250 packets/sec).

### ROS 2 Integration

- **Report IMU noise variance:** Calibration computes per-axis variance but never
  transmits it. Add protocol command (e.g., `0x52`) to query variance for ROS 2
  Imu message covariance fields.

- **Diagnostics status report:** Package battery voltage, uptime, drop count,
  unknown cmd count, and USART errors into a periodic status packet for
  `orbibot/system_status` topic.

### Hardware Abstraction

- **Unified motor API:** Motor control spans `hal_timer.c` (PWM), `motor_driver.c`
  (deadzone), `encoder_driver.c` (direction), and `task_control.c` (ramp). A single
  `motor.h` with `motor_set_speed()` + `motor_read_speed()` + `motor_stop()` would
  simplify the dependency graph.

### Future Scalability

- **Configurable auto-report:** Currently 5 fixed report types at 50Hz each.
  Make report selection and rate configurable via protocol command to reduce
  bandwidth when only specific data is needed (e.g., IMU-only mode).

- **CAN bus passthrough:** ROSMaster V3.0 has SN65HVD230 CAN transceiver on-board.
  Adding CAN RX/TX would enable daisy-chaining external sensor boards or motor
  controllers without additional wiring.

---

## See also
- `firmware-changelog.md` — full change history
