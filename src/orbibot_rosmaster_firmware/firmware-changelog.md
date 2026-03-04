# OrbiBot Firmware Changelog

All notable changes to the OrbiBot ROSMaster firmware.

---

## v2.0.0 — 2026-03-04 (Deep Audit & Hardening)

Major reliability, safety, and code-quality release based on a comprehensive firmware audit comparing against ROSMaster X3 reference, LGDXRobot2 MCU, and Autonomous-Mobile-Robot codebases.

### Critical Bug Fixes

| ID | Fix | Files |
|----|-----|-------|
| BUG-1 | **SPI2 race condition** — `task_imu` is now the sole SPI reader; comm task reads from cache via `imu_task_get_raw_data()` | `task_imu.c`, `protocol.c`, `imu_driver.c` |
| BUG-2 | **FreeRTOS hooks never called** — added `configCHECK_FOR_STACK_OVERFLOW 2` and `configUSE_MALLOC_FAILED_HOOK 1` | `FreeRTOSConfig.h` |
| BUG-3 | **Protocol drop mode stale length** — added `g_cmd_length_drop` for correct packet tracking when both RX buffers full | `protocol.c` |
| BUG-4 | **Duplicate `IMU_UPDATE_RATE_HZ`** — removed duplicate definition | `orbibot_config.h` |

### Concurrency & Thread-Safety

| ID | Fix | Files |
|----|-----|-------|
| RACE-1 | IMU attitude writes now inside `taskENTER_CRITICAL()` — prevents torn reads | `task_imu.c` |
| RACE-2 | Encoder delta uses single-read prev_cnt subtraction — zero lost pulses | `hal_timer.c` |
| RACE-3 | Protocol RX header bytes staged before buffer selection — prevents corruption | `protocol.c` |

### Safety & Reliability

| ID | Fix | Files |
|----|-----|-------|
| SAFE-1 | HardFault/StackOverflow/MallocFailed handlers use direct USART register writes (no heap/printf) | `main.c` |
| SAFE-2 | HSE failure falls back to HSI @ 36MHz instead of hanging in `while(1)` | `main.c` |
| SAFE-3 | Battery critical state sets `g_battery_lockout` — motors refuse non-zero commands until voltage recovers | `task_control.c`, `task_monitoring.c` |
| SAFE-4 | Bounds checks (`>= 4`) on all motor/encoder index parameters | `motor_driver.c`, `encoder_driver.c`, `hal_timer.c` |
| SAFE-5 | Per-task alive counters — watchdog only fed if all critical tasks report alive | `task_monitoring.c`, `task_control.c`, `task_imu.c`, `task_communication.c` |

### Protocol & Communication

| ID | Fix | Files |
|----|-----|-------|
| PROTO-1 | Debug printf disabled for production (`ENABLE_DEBUG_OUTPUT=0`); boot messages gated by `BOOT_PRINTF` macro | `orbibot_config.h`, `main.c` |
| PROTO-2 | Angular velocity clamp uses `MAX_ANGULAR_VELOCITY_RPS` from config (was hardcoded 5.0) | `protocol.c` |
| PROTO-3 | Battery voltage clamped to 0–25.5V before `uint8_t` cast (prevents wrap-around) | `protocol.c` |
| PROTO-4 | Unknown protocol commands counted in `g_unknown_cmd_count` for diagnostics | `protocol.c` |

### Configuration & Build

| ID | Fix | Files |
|----|-----|-------|
| CFG-1 | Version updated to v2.0.0; `FIRMWARE_VERSION_STRING` auto-generated from MAJOR/MINOR/PATCH | `firmware_version.h` |
| CFG-2 | Git commit hash + branch injected at build time via PlatformIO `extra_scripts` | `git_version.py`, `platformio.ini` |
| CFG-3 | Removed `-Wno-implicit-function-declaration`; fixed all in-body `extern` declarations with proper `#include` | `platformio.ini`, `hal_usart.c`, `imu_driver.c` |
| CFG-4 | Added `-Werror` to build flags — all warnings are now build errors | `platformio.ini` |

### Performance

| ID | Fix | Files |
|----|-----|-------|
| PERF-2 | IMU data consolidated into single SPI transaction via `imu_read_both()` (resolved with BUG-1) | `imu_driver.c`, `task_imu.c` |
| PERF-4 | Odometry upgraded from Euler to Midpoint (RK2) integration — less drift during rotation | `odometry.c` |
| PERF-5 | Battery voltage EMA filter (alpha=0.3) — smooths motor inrush transients | `battery_monitor.c` |

### Code Quality & Refactoring

| ID | Fix | Files |
|----|-----|-------|
| REFACT-1 | Encoder direction: 4-way switch → `const int8_t encoder_direction[4]` table | `encoder_driver.c` |
| REFACT-2 | Motor PWM: 4-way switch → `motor_hw_map_t` struct table with CCR pointers | `hal_timer.c` |
| REFACT-3 | Replaced in-body `extern` declarations with proper `#include` headers | `hal_usart.c`, `imu_driver.c` |
| REFACT-4 | Removed duplicate motor GPIO AF_PP init from `hal_timer_pwm_init()` | `hal_timer.c` |
| REFACT-5 | Fixed `flash_storage.h` checksum comment (said XOR, code uses additive sum) | `flash_storage.h` |
| REFACT-6 | Removed 14 dead protocol function codes; kept as commented reference block | `protocol.h` |
| REFACT-7 | Added `robot_error.h` with `robot_err_t` enum (`ROBOT_OK`, `ROBOT_ERR_*`); adopted in IMU driver | `robot_error.h`, `imu_driver.c/h` |
| REFACT-8 | `imu_delay_ms()` uses DWT CYCCNT cycle counter (was iteration-based busy-wait) | `imu_driver.c` |

### Documentation

All 12 documentation-vs-code mismatches fixed across `README.md`, `hardware-doc.md`, and `firmware-architecture.md`:

| ID | Fix |
|----|-----|
| DOC-1 | Firmware version synchronized to v2.0.0 everywhere |
| DOC-2 | SPI Mode corrected: Mode 0 (CPOL_Low, CPHA_1Edge), not Mode 3 |
| DOC-3 | Checksum corrected: additive sum, not XOR |
| DOC-4 | CommTask priority corrected: 7, not 9 |
| DOC-5 | IMU task stack corrected: 1024 words, not 256 |
| DOC-6 | Monitoring task rate corrected: 1Hz, not 10Hz |
| DOC-7 | Battery ADC pin corrected: PC4 (CH14), not PC2 |
| DOC-8 | IMU raw report code corrected: 0x0B, not 0x0E |
| DOC-9 | OLED corrected: software I2C on PA2/PA3, not I2C1 (PB6/PB7 conflicts with TIM4) |
| DOC-10 | Monitoring task stack corrected: 512 words, not 128 |
| DOC-11 | Architecture directory tree rewritten to match actual file layout |
| DOC-12 | Flash map corrected: firmware at 0x0800_0000 (no bootloader offset) |

---

## v1.x — 2025-12 to 2026-02 (Initial Development & First Audit)

### First Firmware Audit (2026-02-18)

Based on comparison with ROSMaster X3 reference, LGDXRobot2 MCU, and Autonomous-Mobile-Robot.

**Critical fixes (C1–C5):**
- C1: Motor stop on critical battery voltage (was OLED-only warning)
- C2: Battery thresholds: 3-level state machine (normal → low_warn → critical_stop)
- C3: `imu_task_get_attitude()` thread safety (taskENTER_CRITICAL)
- C4: `measured_vel` struct write protected with critical section
- C5: `control_get_firmware_odometry()` read protected with critical section

**High-priority fixes (H1–H3):**
- H1: BEEP command length check corrected (>= 6 instead of >= 2)
- H2: Double SPI read in `imu_get_all_raw()` eliminated
- H3: `protocol_is_command_ready()` now checks both buffer flags

**Medium fixes (M2–M5):**
- M2: Function-local `#define` replaced with config constants
- M3: Buzzer low-battery fallback works without OLED enabled
- M4: `encoder_driver_init()` documented dependency on `hal_timer_init()`
- M5: Flash checksum changed from XOR to additive sum

**Low-priority fixes (L1–L3):**
- L1: `WHEEL_CIRCUMFERENCE_M` derived from `WHEEL_DIAMETER_M`
- L2: Unified `PI_F` constant across all files
- L3: `DEBUG_LEVEL` set to 1 (errors only)

**New audit findings (N1–N6):**
- N1: Function code 0x0E collision fixed — `FUNC_RESET_ODOM` assigned 0x09
- N2: HSE startup failure — watchdog moved to first line of `main()`
- N3: Motor test gated behind `#if ENABLE_DEBUG_OUTPUT`
- N4: SPI2 clock lowered from 9MHz to 4.5MHz (within ICM-20948 spec)
- N5: Encoder GPIO changed from IN_FLOATING to IPU (noise rejection)
- N6: DMA TX wait loop has ~2ms timeout (was infinite)

### Initial Implementation (2025-11 to 2026-01)

- STM32F103RCT6 firmware from scratch (replaced Yahboom proprietary binary)
- FreeRTOS with 4 tasks: control (100Hz), IMU (50Hz), communication, monitoring
- ICM-20948 SPI2 driver with gyro calibration, magnetometer, SPI-only mode
- Mecanum kinematics (inverse + forward)
- Multi-level incremental PID motor control
- Yahboom-compatible serial protocol with double-buffered RX
- Quadrature encoder counting via hardware timers
- Battery ADC monitoring with voltage thresholds
- Flash persistence for PID gains and magnetometer calibration
- PlatformIO build system (replaced Keil MDK)

---

## Open Items (Not Yet Implemented)

| ID | Category | Priority | Description |
|----|----------|----------|-------------|
| PERF-1 | Performance | HIGH | Fixed-point PID (STM32F103 has no FPU) |
| PERF-3 | Performance | MEDIUM | DMA for UART RX (reduce ISR overhead) |
| M1 | Feature | MEDIUM | Magnetometer complementary filter for yaw correction |
| I2 | Improvement | LOW | Encoder velocity EMA filtering |
| I3 | Improvement | LOW | Move gyro calibration to RTOS task |
| TEST-1 | Testing | HIGH | Host-side unit tests for PID, kinematics, odometry, protocol |
| TEST-2 | Testing | MEDIUM | Protocol double-buffer stress test |
| TEST-3 | Testing | MEDIUM | Watchdog recovery verification |
| TEST-4 | Testing | LOW | Flash storage wear/corruption test |

---

*Last updated: 2026-03-04*
