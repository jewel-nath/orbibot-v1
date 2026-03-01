# Firmware Audit — Issues & Improvements

**Audited:** 2026-02-18
**Compared against:** ROSMaster X3 reference, LGDXRobot2 MCU, Autonomous-Mobile-Robot

**Status legend:**
- `[ ]` Not fixed
- `[~]` In progress
- `[x]` Fixed

---

## CRITICAL — Must fix (safety / correctness)

### C1 — No motor stop on critical battery voltage
**File:** `src/tasks/task_monitoring.c`
**Problem:** When battery drops below critical voltage (10.5V), the monitoring task only shows
an OLED warning (and only if `ENABLE_OLED_DISPLAY=1`). Motors are **never stopped** when
battery is critically low. This can over-discharge the LiFePO4 pack and cause BMS cutoff
mid-motion (sudden stop = uncontrolled robot).
**Fix:** Call `control_set_velocity(0.0f, 0.0f, 0.0f)` when `voltage < BATTERY_VOLTAGE_CRITICAL`.
Also trigger buzzer regardless of OLED setting.
- [x] Fixed

### C2 — Wrong battery LOW threshold used (11.0V warning skipped entirely)
**File:** `src/tasks/task_monitoring.c:30`
**Problem:** The file defines `VOLTAGE_LOW_THRESHOLD 10.5f` which is the **critical** voltage,
not the low warning voltage. The config has:
- `BATTERY_VOLTAGE_LOW = 11.0V` — 20% remaining, warn user
- `BATTERY_VOLTAGE_CRITICAL = 10.5V` — BMS cutoff, stop motors

But task_monitoring uses 10.5V for "low" and has no 11.0V warning step. The robot jumps
straight from normal to emergency with no warning.
Also `VOLTAGE_HIGH_THRESHOLD = 13.5f` is not in config and makes no physical sense for LiFePO4
4S (full = 14.6V, nominal = 12.8V — 13.5V is a normal operating voltage).
**Fix:** Replace local defines with `BATTERY_VOLTAGE_LOW` and `BATTERY_VOLTAGE_CRITICAL` from
`orbibot_config.h`. Implement a proper 3-level warning: normal → low_warn → critical_stop.
- [x] Fixed

### C3 — `imu_task_get_attitude()` not thread-safe
**File:** `src/tasks/task_imu.c:40-44`
**Problem:** Reads 3 volatile floats (`g_roll`, `g_pitch`, `g_yaw`) with no critical section.
ARM Cortex-M3 does not guarantee atomic multi-word reads. `task_control` reads this at 100Hz
priority 10 while `task_imu` writes at 50Hz priority 8. A preemption between reading g_roll
and g_yaw would give inconsistent attitude data to the yaw PID controller.
**Fix:** Wrap the read in `taskENTER_CRITICAL() / taskEXIT_CRITICAL()`.
- [x] Fixed

### C4 — `measured_vel` written without critical section
**File:** `src/tasks/task_control.c:261-264`
**Problem:** The `measured_vel` struct (3 floats) is written in `task_control` without a
critical section. `control_get_measured_velocity()` reads it from the communication task
(called at 20Hz). Multi-word struct write is not atomic — a torn read could produce garbage
velocity values reported to ROS 2.
**Fix:** Wrap the 3-line write in `taskENTER_CRITICAL() / taskEXIT_CRITICAL()`.
- [x] Fixed

### C5 — `control_get_firmware_odometry()` reads without critical section
**File:** `src/tasks/task_control.c:167-176`
**Problem:** Reads 6 floats from `firmware_odom` with no critical section. `firmware_odom`
is written at 100Hz by `task_control` (lines 268). The communication task calls
`protocol_send_odometry_data()` → `control_get_firmware_odometry()` at 20Hz. Race condition
can produce odometry packets with inconsistent x/y/theta values (torn from two update cycles).
**Fix:** Wrap the 6-float read in `taskENTER_CRITICAL() / taskEXIT_CRITICAL()`.
- [x] Fixed

---

## HIGH — Bugs with functional impact

### H1 — BEEP command length check is wrong (potential buffer overread)
**File:** `src/communication/protocol.c:341`
**Problem:** The BEEP handler checks `if (rx_len >= 2)` before accessing `rx_buf[4]` and
`rx_buf[5]`. But `rx_len` is the **total** packet length. A valid BEEP packet with 2 data bytes
has: header(1) + device_id(1) + length_field(1) + func_code(1) + data[0](1) + data[1](1) +
checksum(1) = 7 bytes → `rx_len = 6` (since `packet_length = length_field + 2`).
The check `>= 2` allows access when total length is just 2, which would read beyond valid data.
**Fix:** Change check to `if (rx_len >= 6)`.
- [x] Fixed

### H2 — Double SPI read in `imu_get_all_raw()` (inconsistent data)
**File:** `src/drivers/imu_driver.c:769-799`
**Problem:** `imu_get_all_raw()` calls `imu_read_raw(&raw)` first, then calls
`imu_read_calibrated(&cal)` which internally calls `imu_read_raw()` again. This reads the IMU
sensor registers **twice** per call — gyro/accel come from the first read, magnetometer comes
from the second read (a different point in time). Creates inconsistent IMU packets.
**Fix:** Read raw once, then apply calibration inline to the same raw data, without a second
hardware read.
- [x] Fixed

### H3 — `protocol_is_command_ready()` only checks primary buffer
**File:** `include/protocol.h:289-292`, `src/tasks/task_communication.c:48`
**Problem:** The helper `protocol_is_command_ready()` returns only `g_cmd_flag` (primary buffer).
`protocol_parse_command()` correctly handles both buffers, but it is only called when
`protocol_is_command_ready()` returns true. If the primary buffer is empty but the secondary
buffer has a command (`g_cmd_flag=0, g_cmd_flag2=1`), the command is **never processed** until
a new command arrives in the primary buffer.
**Fix:** Change return to `return g_cmd_flag || g_cmd_flag2;`.
- [x] Fixed

---

## MEDIUM — Code quality & improvement

### M1 — Pure gyro integration for yaw (drifts over time)
**File:** `src/tasks/task_imu.c:98`
**Problem:** `g_yaw += imu_data.gyro_z * IMU_DT;` — pure gyro integration accumulates drift.
The ICM-20948 + AK09916 magnetometer is fully initialized and reading data, but magnetometer
data is never used for yaw correction. The yaw PID in task_control uses this drifting yaw,
causing incorrect heading correction during extended straight-line operation.
**Fix:** Add a complementary filter that blends gyro integration with magnetometer-derived
heading: `yaw = alpha * (yaw + gyro_z * dt) + (1 - alpha) * mag_yaw`. Alpha ≈ 0.98 at 50Hz.
This is the same approach used by LGDXRobot2.
- [ ] Not yet fixed

### M2 — `#define` inside function body
**File:** `src/communication/protocol.c:428-429`
**Problem:** `#define MAX_LINEAR_SPEED_MM 1000` and `#define MAX_ANGULAR_SPEED 5000` are
defined inside the body of `protocol_handle_motion()`. Function-local `#define` has file scope
(no block scope in C preprocessor), which is misleading. The values should use constants from
`orbibot_config.h` (`MAX_LINEAR_VELOCITY_MPS = 1.0 m/s = 1000 mm/s` already exists).
**Fix:** Remove local defines, use `(int16_t)(MAX_LINEAR_VELOCITY_MPS * 1000)` and define
`MAX_ANGULAR_VELOCITY_RPS` equivalent at module level or use config.
- [x] Fixed

### M3 — Battery warning has no buzzer fallback when OLED disabled
**File:** `src/tasks/task_monitoring.c:66-90`
**Problem:** Low battery warnings are entirely gated by `#if ENABLE_OLED_DISPLAY`. If OLED is
disabled, the robot gives no feedback at all when battery is low. The buzzer (`BUZZER_ON()`) is
available but not used.
**Fix:** Always beep on low battery voltage regardless of OLED state. Keep OLED update inside
the `#if ENABLE_OLED_DISPLAY` guard, but move buzzer action outside the guard.
- [x] Fixed (resolved as part of C1/C2 battery rewrite)

### M4 — `encoder_driver_init()` does nothing (misleading API)
**File:** `src/drivers/encoder_driver.c:14-17`
**Problem:** `encoder_driver_init()` just returns 0 without initializing any hardware.
Encoder hardware is initialized inside `hal_timer_init()`. A caller who sees the function
name would expect encoders to be ready after calling it, but they're not unless `hal_timer_init()`
was called first (which happens in `main.c`). This is a leaky abstraction.
**Fix:** Have `encoder_driver_init()` call `hal_timer_init_encoders()` directly, or at minimum
add an assert or comment documenting the dependency.
- [x] Fixed

### M5 — Flash checksum uses XOR (weak, misses common errors)
**File:** `src/drivers/flash_storage.c:27-37`
**Problem:** The flash checksum is XOR of all bytes. XOR cannot detect: even numbers of
identical bit flips, complete byte transpositions, or common data corruption patterns. The
serial protocol already uses additive sum (sum & 0xFF) which catches more error types.
**Fix:** Replace XOR with additive sum (consistent with protocol.c), or use CRC-8.
- [x] Fixed

---

## LOW — Minor issues

### L1 — `WHEEL_CIRCUMFERENCE_M` hardcoded instead of derived
**File:** `include/orbibot_config.h:29`
**Problem:** `#define WHEEL_CIRCUMFERENCE_M 0.314159f` is hardcoded. If `WHEEL_DIAMETER_M`
is ever changed, this value does not update automatically.
**Fix:** `#define WHEEL_CIRCUMFERENCE_M (3.14159265f * WHEEL_DIAMETER_M)` — derived constant.
- [x] Fixed

### L2 — Inconsistent π constant across files
**File:** `include/orbibot_config.h:470`, `src/control/odometry.c:55`, `src/tasks/task_imu.c:101`
**Problem:** Pi is spelled as `3.14159f`, `3.14159265f`, `3.14159265359f` in different places.
Should use a single `PI_F` constant defined once in `orbibot_config.h`.
- [x] Fixed

### L3 — `DEBUG_LEVEL=2` (Info) with printf() on protocol USART
**File:** `include/orbibot_config.h:270`
**Problem:** `DEBUG_LEVEL=2` enables `DEBUG_INFO()` which calls `printf()`. The protocol USART
(USART1) is used for both protocol packets and debug output. Interleaved debug text corrupts
the binary protocol. The monitoring task already suppresses its printf for this reason.
Other debug prints in protocol.c (`DEBUG_VERBOSE`) could fire during production use.
**Fix:** Set `DEBUG_LEVEL=0` for production, or route debug to a separate USART. For now,
change to `DEBUG_LEVEL=1` (errors only) as a minimum.
- [x] Fixed

---

## Improvements (no bugs, but should be better)

### I1 — Odometry uses simple Euler integration (comment says RK2)
**File:** `src/control/odometry.c:38-52`
**Current:** Comment says "Runge-Kutta 2nd order or simple Euler" but only Euler is implemented.
**Suggestion:** Implement midpoint (RK2) integration for better accuracy at higher speeds:
```c
float mid_theta = odom->theta + robot_vel.omega * dt / 2.0f;
delta_x = (robot_vel.vx * cosf(mid_theta) - robot_vel.vy * sinf(mid_theta)) * dt;
delta_y = (robot_vel.vx * sinf(mid_theta) + robot_vel.vy * cosf(mid_theta)) * dt;
```
- [ ] Improved

### I2 — Add velocity smoothing/filtering on encoder readings
**File:** `src/tasks/task_control.c:249`
**Current:** Raw encoder delta is used directly as measured wheel velocity. Single-tick noise
spikes pass through to the PID.
**Suggestion:** Apply a simple low-pass filter (EMA) to `wheel_speed_mm_s`:
`filtered = alpha * new_speed + (1-alpha) * filtered_prev` with alpha ≈ 0.7 at 100Hz.
LGDXRobot2 uses this pattern.
- [ ] Improved

### I3 — Gyro calibration blocks startup for ~1 second
**File:** `src/drivers/imu_driver.c:556-591`
**Current:** `imu_calibrate()` collects 1000 samples with 1ms delay each = ~1 second busy-wait
before FreeRTOS scheduler starts.
**Suggestion:** Collect fewer samples (200) or move calibration to a startup task that runs
after the scheduler, using `vTaskDelay()` instead of busy-wait.
- [ ] Improved

---

## NEW — Found by deep audit (2026-02-18, second pass)

### N1 — Function code 0x0E collision: FUNC_RESET_ODOM vs FUNC_REPORT_ICM_RAW
**File:** `include/protocol.h`
**Problem:** Both `FUNC_RESET_ODOM` and `FUNC_REPORT_ICM_RAW` are assigned `0x0E`. An incoming
`0x0E` packet from ROS 2 dispatches to `protocol_handle_reset_odom()`. The outgoing ICM raw
report also uses `0x0E`. The Yahboom reference uses `0x0E` = ICM raw and `0x0F` = reset state.
If the ROS driver ever receives an echo it will misparse it as ICM raw data.
**Fix:** Assign `FUNC_RESET_ODOM` a unique code (e.g., `0x0F`) and update firmware + ROS driver.
- [x] Fixed — assigned 0x09, updated protocol.h + rosmaster_driver.py atomically

### N2 — HSE startup failure causes unrecoverable hang
**File:** `src/main.c:76-81`
**Problem:** If the 8 MHz crystal fails to start (e.g., cold start, vibration), the MCU enters
`while(1)` at clock init — before the IWDG watchdog is initialized (watchdog init happens after
`vTaskStartScheduler()`, which is unreachable). The robot hangs permanently with no recovery.
**Fix:** Initialize IWDG early (before RCC clock switch), or implement HSI fallback (run at
36 MHz on internal RC if HSE fails).
- [x] Fixed — hal_watchdog_init() moved to first line of main()

### N3 — Motor test fires on every boot (safety risk)
**File:** `src/main.c:234-235`
**Problem:** `motorTest()` pulses all four motors briefly on every power-up — even when the robot
is on a surface with obstacles nearby. This is a safety risk in production.
**Fix:** Gate behind `#if ENABLE_DEBUG_OUTPUT` or a button-press check at boot.
- [x] Fixed — motorTest() wrapped in #if ENABLE_DEBUG_OUTPUT

### N4 — SPI2 clock (9 MHz) exceeds ICM-20948 max for register reads (7 MHz)
**File:** `src/hal/hal_spi.c:61`
**Problem:** SPI2 is configured at APB1/4 = 9 MHz. ICM-20948 datasheet specifies max 7 MHz for
register read operations. At 9 MHz, occasional SPI read errors are possible (register reads can
glitch at speeds above spec).
**Fix:** Change prescaler to APB1/8 = 4.5 MHz for reliable IMU reads, or split to slow init /
fast data (ICM allows faster for burst reads only).
- [x] Fixed — SPI_BaudRatePrescaler_8 (4.5 MHz)

### N5 — Encoder GPIO uses IN_FLOATING (susceptible to noise on long wires)
**File:** `src/hal/hal_timer.c` (all encoder init functions)
**Problem:** All encoder GPIO inputs use `GPIO_Mode_IN_FLOATING`. For long motor wires or noisy
environments, floating inputs can pick up glitches when the motor is at rest or spinning slowly.
**Fix:** Change to `GPIO_Mode_IPU` (input pull-up) for more reliable low-speed reading.
- [x] Fixed — all 4 encoder timers (TIM2/3/4/5) updated to GPIO_Mode_IPU

### N6 — DMA TX wait loop has no timeout
**File:** `src/hal/hal_usart.c`
**Problem:** `while (DMA_GetCurrDataCounter(DMA1_Channel4) != 0)` has no timeout. If a DMA
transfer stalls (USART hardware fault), the comm task hangs indefinitely. The watchdog would
eventually reset, but no error is reported and the reset takes up to the IWDG period.
**Fix:** Add a timeout counter and return an error if DMA stall is detected.
- [x] Fixed — ~2ms timeout (144000 cycles), disables channel on stall

---

## Fix Order (priority sequence)

### Completed
1. [x] C1 + C2 — Battery safety (3-level state machine, motor stop, buzzer)
2. [x] C3 — IMU attitude thread safety (taskENTER_CRITICAL)
3. [x] C4 + C5 — measured_vel + firmware_odom thread safety
4. [x] H1 — BEEP length check (>= 6)
5. [x] H2 — Double SPI read in imu_get_all_raw
6. [x] H3 — protocol_is_command_ready secondary buffer
7. [x] M2 — #define inside function → static const
8. [x] M3 — Buzzer fallback (resolved in C1/C2 rewrite)
9. [x] M4 — encoder_driver_init comment + counter reset
10. [x] M5 — Flash checksum XOR → additive sum
11. [x] L1 + L2 + L3 — PI_F constant, derived circumference, debug level=1
12. [x] Issue #5 — Watchdog from task_control (100Hz) for critical task hang detection
13. [x] Issue #4 — Verified flash storage checksum already implemented

---

## Recent Fixes (March 2026)

### Issue #5: Watchdog Feed from Critical Control Task
**File:** `src/tasks/task_control.c`  
**Problem:** Watchdog was only fed in `task_monitoring` (1Hz). If `task_control` hung, watchdog would not trigger.  
**Fix:** Added `hal_watchdog_feed()` call in `task_control.c` at 100Hz, ensuring watchdog triggers if the critical control task hangs. Watchdog is now fed from both tasks for redundancy.

### Issue #4: Flash Storage Checksum Verification
**File:** `src/drivers/flash_storage.c`  
**Problem:** Document claimed no checksum on flash storage.  
**Status:** ✅ Verified - Additive checksum was already implemented in `calculate_checksum()`, `flash_storage_load()`, and `flash_storage_is_valid()`. Checksum covers PID gains and magnetometer calibration data.

### Issue #2: Yaw Control Threshold Configuration
**File:** `src/tasks/task_control.c`, `include/orbibot_config.h`  
**Problem:** Document claimed threshold was hardcoded.  
**Status:** ✅ Verified - Code already uses `YAW_ENABLE_THRESHOLD` from config (0.05f). Configurable without recompilation via header file.

### Next (in order)
12. [x] N1 — Fix 0x0E function code collision (protocol.h + ROS driver)
13. [x] N2 — HSE startup watchdog (main.c)
14. [x] N3 — Gate motorTest() behind debug flag (main.c)
15. [x] N4 — Lower SPI clock to 4.5 MHz for ICM-20948 (hal_spi.c)
16. [x] N5 — Encoder GPIO IN_FLOATING → IPU (hal_timer.c)
17. [x] N6 — DMA TX timeout (hal_usart.c)
18. [ ] M1 — Magnetometer complementary filter for yaw (task_imu.c)
19. [ ] I1 — RK2 odometry integration (odometry.c)
20. [ ] I2 — Encoder velocity EMA filter (task_control.c)
21. [ ] I3 — Gyro calibration move to RTOS task (imu_driver.c)
