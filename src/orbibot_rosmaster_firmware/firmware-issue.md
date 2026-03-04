# OrbiBot Firmware — Deep Analysis: Issues, Improvements & Refactoring

**Analyzed by**: Claude (deep firmware review)
**Date**: 2026-03-04
**Firmware Version**: v2.0.0
**Review**: I am already run a previous firmware with working condition. It almost work fine but found some odom drift issue, before I am calculate odom on ros2 node (on raspbery pi), now its calculate on firmware and now using magnetometer ( I am not test this magnetometer yet). So Its my second version orbibot firmware.
**Scope**: All files under `src/`, `include/`, `lib/`, `README.md`, `firmware-architecture.md`, `hardware-doc.md`


---

## Table of Contents

1. [Critical Bugs](#1-critical-bugs)
2. [Concurrency & Thread-Safety Issues](#2-concurrency--thread-safety-issues)
3. [Protocol & Communication Issues](#3-protocol--communication-issues)
4. [Configuration & Build Issues](#4-configuration--build-issues)
5. [Safety & Reliability Issues](#5-safety--reliability-issues)
6. [Documentation vs Code Discrepancies](#6-documentation-vs-code-discrepancies)
7. [Performance Improvements](#7-performance-improvements)
8. [Code Quality & Refactoring Ideas](#8-code-quality--refactoring-ideas)
9. [Testing Gaps](#9-testing-gaps)
10. [Previously Resolved (Preserved)](#10-previously-resolved-preserved)

---

## 1. Critical Bugs

### BUG-1: SPI2 Concurrent Access Race Condition (task_imu vs task_communication)

**Severity**: CRITICAL
**Files**: `tasks/task_imu.c`, `tasks/task_communication.c`, `communication/protocol.c`, `drivers/imu_driver.c`

**Description**:
Both `task_imu` (priority 8) and `task_communication` (priority 7) perform SPI2 transactions to the IMU. When `task_communication` calls `protocol_send_imu_raw_data()` → `imu_get_all_raw()` → `imu_read_raw()`, it starts SPI2 communication. If `task_imu` (higher priority) preempts mid-transaction and also calls `imu_read_calibrated()` → `imu_read_raw()`, the CS line and SPI data register will be corrupted.

**Repro scenario**:
1. Comm task at count=11 calls `protocol_send_imu_raw_data()`
2. `imu_read_raw()` asserts CS low, sends register address
3. IMU task wakes (higher priority), preempts
4. IMU task also calls `imu_read_raw()`, asserts CS low again
5. Both transactions produce garbage data

**Fix**: Add a FreeRTOS mutex around all SPI2 operations, or restructure so only `task_imu` reads the IMU and caches data for `task_communication` to use.

**Review**: Good finding, need to fix this "task_imu" read the IMU.

---

### BUG-2: FreeRTOS Hook Functions Never Called — Config Macros Missing

**Severity**: CRITICAL
**Files**: `include/FreeRTOSConfig.h`, `src/main.c`

**Description**:
`main.c` defines `vApplicationStackOverflowHook()` and `vApplicationMallocFailedHook()`, but `FreeRTOSConfig.h` does **not** enable the corresponding macros:

```c
// MISSING from FreeRTOSConfig.h:
#define configCHECK_FOR_STACK_OVERFLOW  2   // needed for vApplicationStackOverflowHook
#define configUSE_MALLOC_FAILED_HOOK    1   // needed for vApplicationMallocFailedHook
```

Without these macros, FreeRTOS will **never call** the hooks. Stack overflows and heap exhaustion will cause silent corruption instead of a controlled halt with diagnostic output.

**Fix**: Add both macros to `FreeRTOSConfig.h`. Use `configCHECK_FOR_STACK_OVERFLOW = 2` for the most thorough check (pattern-fill method).

**Review**: Fix it.

**Status**: ✅ FIXED — Added `configCHECK_FOR_STACK_OVERFLOW 2` and `configUSE_MALLOC_FAILED_HOOK 1` to `FreeRTOSConfig.h`.

---

### BUG-3: Protocol RX State Machine — Drop Mode Uses Stale Length

**Severity**: HIGH
**Files**: `communication/protocol.c`

**Description**:
When both RX buffers are full (`g_rx_active_buffer = 2`, drop mode), the state machine still enters `RX_STATE_READ_DATA`. In that state, the completion check uses:

```c
uint8_t target_length = (g_rx_active_buffer == 0) ? g_cmd_length : g_cmd_length2;
```

When `g_rx_active_buffer == 2`, this falls to the `else` branch and reads `g_cmd_length2`, which holds the length of the *previous* secondary buffer packet — not the current dropped packet. The actual packet length for the dropped packet was never stored.

This can cause the state machine to:
- Exit `READ_DATA` too early (truncating bytes from a *future* valid packet header)
- Stay in `READ_DATA` too long (consuming bytes from the next packet)

**Fix**: Store the dropped packet length in a separate variable, or track it in the state machine:

**Review**: Fix it.

**Status**: ✅ FIXED — Added `g_cmd_length_drop` to track dropped packet length. `RX_STATE_READ_DATA` now uses a 3-way check for primary/secondary/drop buffer lengths.

---

### BUG-4: `IMU_UPDATE_RATE_HZ` Defined Twice in `orbibot_config.h`

**Severity**: MEDIUM
**File**: `include/orbibot_config.h`

**Description**:
`IMU_UPDATE_RATE_HZ` is defined at line 193 (Control Parameters section) and again at line 228 (IMU Configuration section), both as `50`. While the values match today, this is a maintenance hazard — changing one without the other will cause a silent macro redefinition warning (or error with `-Werror`) and undefined behavior depending on which definition wins.

```c
// Line 193 (Control Parameters):
#define IMU_UPDATE_RATE_HZ          50

// Line 228 (IMU Configuration):
#define IMU_UPDATE_RATE_HZ          50   // DUPLICATE
```

**Fix**: Remove the duplicate at line 228. Keep the single definition in the Control Parameters section.

**Review**: Fix it.

**Status**: ✅ FIXED — Removed duplicate, kept single definition in Control Parameters section.

---

## 2. Concurrency & Thread-Safety Issues

### RACE-1: IMU Attitude Writes Not Protected in `task_imu`

**Severity**: MEDIUM
**File**: `tasks/task_imu.c`

**Description**:
`g_roll`, `g_pitch`, and `g_yaw` are written directly without a critical section (lines 104–137), but `imu_task_get_attitude()` reads them *inside* a critical section. On Cortex-M3, individual 32-bit float writes are atomic, but the *consistency between all three values* is not guaranteed.

If `task_control` (priority 10) preempts `task_imu` between writing `g_roll` and `g_yaw`, the `imu_task_get_attitude()` call from `task_control` could read `g_roll` from the new frame and `g_yaw` from the old frame — a torn read that produces inconsistent attitude data for yaw correction.

**Fix**: Write all three values inside a critical section:

```c
taskENTER_CRITICAL();
g_roll = new_roll;
g_pitch = new_pitch;
g_yaw = new_yaw;
taskEXIT_CRITICAL();
```

**Review**: Fix it.

**Status**: ✅ FIXED — Attitude computed into local variables, then written atomically inside `taskENTER_CRITICAL()`/`taskEXIT_CRITICAL()`. Yaw read also protected when used for gyro integration.

---

### RACE-2: Encoder Delta Read-Then-Reset Not Atomic

**Severity**: LOW
**File**: `hal/hal_timer.c`

**Description**:
`hal_timer_read_encoder_delta()` reads the counter and resets to midpoint in two separate operations:

```c
delta = (int16_t)TIM2->CNT - ENCODER_MIDPOINT;
TIM2->CNT = ENCODER_MIDPOINT;
```

Encoder pulses arriving between the read and reset are lost. At 100Hz with typical encoder rates this loses ~0-2 counts per read (negligible), but under high-speed motion or with electrical noise, it could accumulate.

**Fix**: Disable the timer briefly, or use an interrupt to capture the count atomically. Alternatively, accept the tiny error and document it.

**Review**: think clearly and fix this with best solution.

**Status**: ✅ FIXED — Replaced midpoint-reset with a single-read delta pattern using `encoder_prev_cnt[]`. 16-bit modular subtraction handles counter wrap. Zero lost pulses since there is no write to the timer counter during reads.

---

### RACE-3: `protocol_receive_byte()` Writes to Primary Buffer Header During Processing

**Severity**: LOW
**File**: `communication/protocol.c`

**Description**:
In states `RX_STATE_WAIT_HEADER` and `RX_STATE_WAIT_DEVICE`, bytes are written to `g_rx_buffer[0]` and `g_rx_buffer[1]` unconditionally. If `g_cmd_flag` is set (primary buffer being processed by the task), these writes corrupt the buffer's header bytes. This doesn't usually cause problems because the task reads `func_code` from `rx_buf[3]` and data from `rx_buf[4+]`, but it violates the double-buffer invariant.

**Fix**: Only write to `g_rx_buffer` if `g_cmd_flag == 0`, or use a separate staging area for header bytes.

**Review**: think clearly and fix this with best solution.

**Status**: ✅ FIXED — Header and device bytes now stage in `g_rx_staged_header`/`g_rx_staged_device`, then copy to the correct target buffer only after buffer selection in `RX_STATE_WAIT_LENGTH`.

---

## 3. Protocol & Communication Issues

### PROTO-1: `printf()` and Protocol TX Share USART1 — Packet Corruption

**Severity**: HIGH
**Files**: `hal/hal_usart.c`, `communication/protocol.c`

**Description**:
Debug `printf()` output uses `_write()` → `hal_usart_send_byte()` (blocking, byte-by-byte), while protocol packets use `hal_usart_send_bytes()` (DMA). If a printf fires while a DMA transfer is in progress — or if a DMA transfer starts during printf — the USART data stream will be interleaved, corrupting protocol packets that the ROS 2 host is parsing.

With `DEBUG_LEVEL = 1` and `ENABLE_DEBUG_OUTPUT = 1`, error messages can fire at any time from any task.

**Fix options**:
1. Route debug output to a different USART (USART2/3)
2. Use a printf buffer with DMA (serialized with protocol TX)
3. Set `ENABLE_DEBUG_OUTPUT = 0` and `DEBUG_LEVEL = 0` for production
4. Gate all printf output behind a FreeRTOS mutex shared with DMA TX

**Review**: When I write version 1 firmwire robot motor not moving. thats why I including this. now robot is moving. think what can I do for this issue, suggest the best solution. 

---

### PROTO-2: Angular Velocity Clamp Mismatch — Config Says 2.0 rad/s, Protocol Allows 5.0 rad/s

**Severity**: MEDIUM
**File**: `communication/protocol.c`

**Description**:
`orbibot_config.h` defines `MAX_ANGULAR_VELOCITY_RPS = 2.0f` (2000 mrad/s), but `protocol_handle_motion()` clamps angular speed to 5000 mrad/s:

```c
static const int16_t MAX_ANGULAR_SPEED_MRAD = 5000; // mrad/s — allows 5.0 rad/s
```

The comment says "gives extra headroom" but this contradicts the safety limit. The robot could be commanded at 2.5x the intended maximum angular velocity.

**Fix**: Use the config constant:

**Review**: okay, keep config constant.

**Status**: ✅ FIXED — Both linear and angular clamps now derive from `MAX_LINEAR_VELOCITY_MPS` and `MAX_ANGULAR_VELOCITY_RPS` config constants.

---

### PROTO-3: Battery Voltage Report Truncates to `uint8_t` — Max 25.5V, Precision 0.1V

**Severity**: LOW
**File**: `communication/protocol.c`

**Description**:
Battery voltage is sent as a single `uint8_t`:

```c
data[6] = (uint8_t)(voltage * 10.0f);  // Max representable: 25.5V
```

For a 14.6V battery this works (146 fits in uint8), but:
- Precision is only 0.1V (ROS 2 side can only distinguish 0.1V steps)
- No negative voltage protection (if ADC returns noise, cast wraps)
- LiFePO4 voltage curve is relatively flat; 0.1V resolution may not distinguish charge states well

**Fix**: Consider using 16-bit reporting (int16, voltage × 100) for 0.01V precision, or at minimum add a `if (voltage < 0) voltage = 0` guard.

**Review**: Okay, fix it.

**Status**: ✅ FIXED — Added negative voltage guard and upper clamp (25.5V). Kept uint8_t format to maintain protocol compatibility with ROS 2 driver.

---

### PROTO-4: Many Declared Function Codes Are Unhandled

**Severity**: LOW
**File**: `include/protocol.h`, `communication/protocol.c`

**Description**:
`protocol.h` declares 25+ function codes (servo, RGB, Ackerman, CAN, test mode, etc.), but `protocol_parse_command()` only handles 10 of them. Unknown codes fall to the `default: break` case silently. This is fine for unused features, but:
- `FUNC_RESET_FLASH (0xA0)` is declared but unhandled — a host sending this expects something to happen
- `FUNC_CAR_TYPE (0x17)` is declared but ignored — may confuse ROS 2 drivers

**Fix**: Add explicit handling or at minimum a NACK/error response for known-but-unimplemented codes.

**Review**: For now orbibot not using this protocol, so think and do, what need to do.

---

## 4. Configuration & Build Issues

### CFG-1: `FIRMWARE_VERSION_STRING` Not Derived from Version Macros

**Severity**: LOW
**File**: `include/firmware_version.h`

**Description**:
The version components (`FIRMWARE_VERSION_MAJOR/MINOR/PATCH`) and the string `FIRMWARE_VERSION_STRING "v1.0.0"` are maintained independently. Updating one without the other causes version mismatch.

**Fix**: Use macro stringification:

```c
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define FIRMWARE_VERSION_STRING \
    "v" TOSTRING(FIRMWARE_VERSION_MAJOR) "." \
        TOSTRING(FIRMWARE_VERSION_MINOR) "." \
        TOSTRING(FIRMWARE_VERSION_PATCH)
```

**Review**: Firmware version 2.

**Status**: ✅ FIXED — Version updated to 2.0.0, `FIRMWARE_VERSION_STRING` now auto-generated via macro stringification.

---

### CFG-2: Git Commit Hash Not Populated by Build System

**Severity**: LOW
**File**: `include/firmware_version.h`, `platformio.ini`

**Description**:
`GIT_COMMIT_HASH` and `GIT_BRANCH` default to `"unknown"`. The `platformio.ini` does not include a `build_flags` entry to populate them from git.

**Fix**: Add to `platformio.ini`:

```ini
build_flags =
    ...
    -D GIT_COMMIT_HASH=\"$(shell git rev-parse --short HEAD)\"
    -D GIT_BRANCH=\"$(shell git rev-parse --abbrev-ref HEAD)\"
```

Or use PlatformIO's `extra_scripts` for cross-platform git info injection.

**Review**: use build flags.

---

### CFG-3: `-Wno-implicit-function-declaration` Suppresses Real Errors

**Severity**: MEDIUM
**File**: `platformio.ini`

**Description**:
The build suppresses implicit function declaration warnings:

```ini
-Wno-implicit-function-declaration
```

This hides cases where a function is called without a proper `#include` or forward declaration. On Cortex-M, calling a function with the wrong assumed signature can cause stack corruption. The `extern void protocol_receive_byte()` in `hal_usart.c` and `extern void imu_task_get_attitude()` in `imu_driver.c` are examples of this pattern — using `extern` declarations inside function bodies instead of proper includes.

**Fix**: Remove `-Wno-implicit-function-declaration`, add proper `#include` directives, and fix any resulting warnings.

**Review**: fix it.

---

### CFG-4: `build_unflags = -Werror` Weakens Build Safety

**Severity**: LOW
**File**: `platformio.ini`

**Description**:
Removing `-Werror` means all warnings are non-fatal. Combined with `-Wall -Wextra`, this produces warnings that are seen but never fixed. For a safety-critical firmware controlling physical motors, warnings should be treated as errors.

**Fix**: Remove `build_unflags = -Werror` and fix all warnings. Add `-Werror` to `build_flags` for production builds.

**Review**: Fix it.

---

## 5. Safety & Reliability Issues

### SAFE-1: `HardFault_Handler` Calls `printf()` — May Cause Double Fault

**Severity**: MEDIUM
**File**: `src/main.c`

**Description**:
`HardFault_Handler()`, `vApplicationStackOverflowHook()`, and `vApplicationMallocFailedHook()` all call `printf()`, which:
1. Uses the heap (newlib printf) — may fail if heap is exhausted
2. Accesses USART1 peripheral — may fault if peripheral bus is corrupted
3. Could cause a secondary hard fault, making diagnosis impossible

**Fix**: In fault handlers, use direct register-level USART output (no library calls), or write fault info to a reserved RAM region that survives reset, then output it on next boot.

**Review**: Fix it.


---

### SAFE-2: `systemClockConfig()` Enters Infinite Loop on HSE Failure — Before Watchdog

**Severity**: MEDIUM
**File**: `src/main.c`

**Description**:
If HSE fails, `systemClockConfig()` hangs in `while(1)`. The code comment says "set BOOT0=HIGH, press RESET" but in production, the robot would be permanently bricked until physical intervention. The watchdog is started before `systemClockConfig()`, which should eventually reset the MCU, but the `while(1)` at line 80 has no error recovery path.

**Fix**: On HSE failure, fall back to HSI (8MHz internal oscillator) at reduced clock speed. Log the error and continue with degraded performance rather than halting completely.

**Review**: think and try to make a best solution for this issue.

---

### SAFE-3: Battery Critical State Does Not Disable Motor Commands

**Severity**: MEDIUM
**File**: `tasks/task_monitoring.c`

**Description**:
When battery reaches critical voltage, `control_set_velocity(0,0,0)` is called once. But nothing prevents a new motion command from immediately restarting the motors. If the ROS 2 node keeps sending velocity commands, the motors will restart, drain the battery further, and risk BMS hard cutoff during motion.

**Fix**: Add a `battery_lockout` flag that `control_set_velocity()` checks. Motors should remain disabled until voltage recovers above a hysteresis threshold (e.g., `BATTERY_VOLTAGE_LOW + 0.5V`).

**Review**: Fix it.

---

### SAFE-4: No Bounds Check on Motor/Encoder Index Parameters

**Severity**: MEDIUM
**Files**: `drivers/motor_driver.c`, `drivers/encoder_driver.c`, `hal/hal_timer.c`

**Description**:
Functions like `motor_set_speed(motor, speed)`, `encoder_read_delta(encoder)`, `hal_timer_set_motor_pwm(motor, pwm)`, and `hal_timer_read_encoder_delta(encoder)` accept a `uint8_t` index but do not validate `motor < 4` or `encoder < 4`. An out-of-bounds index silently falls through the `switch` statement doing nothing — or worse, in future code changes, could cause memory corruption.

**Fix**: Add `if (motor >= 4) return;` guards at the top of each function.

**Review**: Fix it.

**Status**: ✅ FIXED — Added `>= 4` bounds checks in `motor_set_speed()`, `encoder_read_delta()`, `encoder_get_count()`, `encoder_reset()`, `hal_timer_set_motor_pwm()`, `hal_timer_read_encoder_delta()`, `hal_timer_get_encoder_count()`, `hal_timer_reset_encoder()`.

---

### SAFE-5: Watchdog Fed from Two Tasks — Masks Failure of Either

**Severity**: LOW
**Files**: `tasks/task_control.c`, `tasks/task_monitoring.c`

**Description**:
The watchdog is fed from both `task_control` (100Hz) and `task_monitoring` (1Hz). If `task_monitoring` hangs, `task_control` continues feeding the watchdog, masking the failure. If `task_control` hangs, `task_monitoring` continues feeding.

The intent was redundancy (Issue #5), but the result is that neither task's hang is reliably detected by the watchdog.

**Fix**: Only feed the watchdog from the lowest-priority task (`task_monitoring`). Implement per-task alive counters that `task_monitoring` checks before feeding the watchdog. If any critical task's counter hasn't incremented, withhold the feed.

**Review**: think and give a better fix.

---

## 6. Documentation vs Code Discrepancies

These issues were found by cross-referencing `README.md`, `firmware-architecture.md`, and `hardware-doc.md` against the actual source code.

### DOC-MISMATCH-1: Firmware Version — README Says v2.0.0, Code Says v1.0.0

**Severity**: MEDIUM
**Files**: `README.md` (line 506), `include/firmware_version.h`

| Source | Version |
|--------|---------|
| `README.md` | v2.0.0 |
| `firmware_version.h` MAJOR/MINOR/PATCH | 1.0.0 |
| `firmware_version.h` VERSION_STRING | "v1.0.0" |
| `firmware-issue.md` (old header) | v2.0.0 |

**Fix**: Synchronize all version references. If the firmware is at v2.0.0, update `firmware_version.h`.

**Review**: version is v2.0.0

---

### DOC-MISMATCH-2: SPI Mode — hardware-doc.md Says Mode 3, Code Uses Mode 0

**Severity**: HIGH (could cause confusion during hardware debug)
**Files**: `hardware-doc.md`, `hal/hal_spi.c`

| Source | CPOL | CPHA | SPI Mode |
|--------|------|------|----------|
| `hardware-doc.md` | `SPI_CPOL_High` | `SPI_CPHA_2Edge` | **Mode 3** |
| Actual `hal_spi.c` | `SPI_CPOL_Low` | `SPI_CPHA_1Edge` | **Mode 0** |

The ICM-20948 supports both Mode 0 and Mode 3, so the code works, but the documentation would mislead anyone trying to debug SPI issues.

**Fix**: Update `hardware-doc.md` SPI Configuration to match the actual code (Mode 0).

**Review**: okay, match this.

---

### DOC-MISMATCH-3: Checksum Algorithm — hardware-doc.md Says XOR, Code Uses Additive Sum

**Severity**: HIGH (would cause protocol failures if someone implements from docs)
**Files**: `hardware-doc.md`, `communication/protocol.c`

| Source | Algorithm |
|--------|-----------|
| `hardware-doc.md` | `checksum = Device_ID ^ Length ^ Function ^ Data[0] ^ ...` (XOR) |
| `README.md` | "additive sum... truncated to uint8_t" (correct) |
| `firmware-architecture.md` | "additive sum... (NOT XOR)" (correct) |
| Actual `protocol.c` | `sum += data[i]` (additive sum) |
| `flash_storage.h` comment | "XOR checksum" (wrong) |

Three sources say additive, two say XOR. The code is additive.

**Fix**: Update `hardware-doc.md` checksum description and `flash_storage.h` comment.

**Review**: My firmware can commucate with ros2 hardware node to stm32 firmware, so update the docs according to code, may be its my mistake.

---

### DOC-MISMATCH-4: CommTask Priority — Docs Say 9, Code Uses 7

**Severity**: MEDIUM
**Files**: `README.md`, `firmware-architecture.md`, `hardware-doc.md`, `src/main.c`

| Source | Priority | Stack |
|--------|----------|-------|
| `README.md` | 9 | 2048-byte (512 words) |
| `firmware-architecture.md` | 9 | 512 words |
| `hardware-doc.md` | 9 | 512 words |
| Actual `main.c` | **7** | 512 words (2048 bytes) |

The actual priority was lowered to 7 (comment says "matches reference firmware"), but no documentation was updated.

**Fix**: Update all three docs to show priority 7.

**Review**: yes, update to 7.

---

### DOC-MISMATCH-5: IMU Task Stack — hardware-doc.md Says 256 Words, Code Uses 1024

**Severity**: MEDIUM
**File**: `hardware-doc.md`, `include/orbibot_config.h`

| Source | task_imu Stack |
|--------|----------------|
| `hardware-doc.md` | 256 words |
| Actual `orbibot_config.h` | `TASK_IMU_STACK = 1024` (4096 bytes) |

**Fix**: Update `hardware-doc.md` FreeRTOS task table.

**Review**: update docs

---

### DOC-MISMATCH-6: Monitoring Task Rate — README Says 10Hz, Code Is 1Hz

**Severity**: LOW
**Files**: `README.md`, `tasks/task_monitoring.c`

| Source | Rate |
|--------|------|
| `README.md` | "10Hz, priority 5" |
| `firmware-architecture.md` | "1Hz" (correct) |
| Actual code | `vTaskDelay(pdMS_TO_TICKS(1000))` = **1Hz** |

**Fix**: Update `README.md` to say 1Hz.

**Review**: update docs

---

### DOC-MISMATCH-7: Battery ADC Pin — README Says PC2, Code Uses PC4

**Severity**: MEDIUM (misleading for hardware debug)
**Files**: `README.md`, `include/orbibot_config.h`

| Source | ADC Pin |
|--------|---------|
| `README.md` debug table | "ADC on PC2" |
| `orbibot_config.h` | `BATTERY_ADC_PIN = GPIO_Pin_4` on `GPIOC` = **PC4** |
| `orbibot_config.h` | `BATTERY_ADC_CHANNEL = ADC_Channel_14` (PC4 is CH14) |

**Fix**: Update README debug table to say "ADC on PC4".

**Review**: update docs

---

### DOC-MISMATCH-8: IMU Raw Report Function Code — README Says 0x0E, Code Sends 0x0B

**Severity**: HIGH (would break protocol parsing if someone uses docs)
**Files**: `README.md`, `communication/protocol.c`, `include/protocol.h`

| Source | IMU Raw Report Code |
|--------|---------------------|
| `README.md` auto-report table | `0x0E` (`REPORT_ICM_RAW`) |
| `firmware-architecture.md` | `0x0E` (`REPORT_ICM_RAW`) |
| Actual `protocol_send_imu_raw_data()` | `FUNC_REPORT_MPU_RAW` = **`0x0B`** |

The code sends IMU raw data with function code `0x0B`, but docs say `0x0E`. A ROS 2 driver built from the docs would never receive IMU raw data.

**Fix**: Update docs to say `0x0B`, or rename `FUNC_REPORT_MPU_RAW` to `FUNC_REPORT_ICM_RAW` and use `0x0E` (which is already defined but unused).

**Review**: fix this.

---

### DOC-MISMATCH-9: OLED Interface — hardware-doc.md Says I2C1, Code Uses Software I2C on PA2/PA3

**Severity**: LOW
**Files**: `hardware-doc.md`, `include/orbibot_config.h`

| Source | OLED Interface |
|--------|----------------|
| `hardware-doc.md` | I2C1 (PB6/PB7) |
| `orbibot_config.h` | Software I2C on **PA2/PA3** |
| Comment in config | "Hardware I2C1 (PB6/PB7) CONFLICTS with TIM4 encoder (M2)!" |

Hardware I2C1 can't be used because PB6/PB7 are needed for M2 encoder (TIM4).

**Fix**: Update `hardware-doc.md` OLED section to document the software I2C workaround.

**Review**: update docs

---

### DOC-MISMATCH-10: Monitoring Task Stack — hardware-doc.md Says 128 Words, Code Uses 512

**Severity**: LOW
**File**: `hardware-doc.md`, `include/orbibot_config.h`

| Source | task_monitoring Stack |
|--------|----------------------|
| `hardware-doc.md` | 128 words |
| Actual `orbibot_config.h` | `TASK_MONITORING_STACK = 512` (2048 bytes) |

**Fix**: Update `hardware-doc.md` FreeRTOS task table.

**Review**: update docs

---

### DOC-MISMATCH-11: Architecture Doc Directory Structure Doesn't Match Reality

**Severity**: LOW
**File**: `firmware-architecture.md`

The architecture doc shows files/directories that don't exist:

| Documented | Actual |
|------------|--------|
| `src/core/system_init.c` | Clock init is in `main.c` |
| `src/core/freertos_config.c` | Config is in `include/FreeRTOSConfig.h` |
| `src/core/stm32f1xx_it.c` | Interrupt handlers are in `main.c` |
| `src/communication/command_handler.c` | Doesn't exist; handled in `protocol.c` |
| `lib/printf/` | Doesn't exist; uses GCC newlib `_write()` |
| `lib/STM32F1xx_HAL/` | Actually `lib/STM32F10x_StdPeriph_Driver/` |

**Fix**: Update architecture doc directory tree to match actual file layout.

**Review**: update docs

---

### DOC-MISMATCH-12: Flash Memory Map — hardware-doc.md Shows Bootloader Offset, Code Uses Base

**Severity**: LOW
**File**: `hardware-doc.md`

`hardware-doc.md` says firmware starts at `0x0800_4000` (after 16KB bootloader), but PlatformIO's default linker script for STM32F103RC starts firmware at `0x0800_0000`. The flash storage page at `0x0803_F800` is correct.

**Fix**: Remove the bootloader reference or clarify this only applies when using a custom bootloader.

**Review**: fix this.

---

## 7. Performance Improvements

### PERF-1: Fixed-Point PID — STM32F103 Has No FPU

**Priority**: HIGH
**Files**: `control/pid_controller.c`, `tasks/task_control.c`

**Description**:
All PID calculations use `float` arithmetic. The STM32F103 Cortex-M3 has no hardware FPU — every float operation is a software library call (~20-50 cycles per operation vs. 1 cycle for integer). The PID loop runs at 100Hz with 4 motors, plus multi-level gain interpolation with `fabsf()`, each iteration.

**Estimated Impact**: Converting PID to Q16.16 or Q8.24 fixed-point would reduce control loop execution time by ~50%, freeing CPU for additional features or allowing higher control rates.

**Approach**:
- Define `typedef int32_t fixed_t` with Q16.16 format
- Replace float multiplies with `fixed_mul(a, b) = ((int64_t)a * b) >> 16`
- Keep float only for configuration API (convert to fixed-point at set time)

**Review**: think and write the best solution for this.

---

### PERF-2: Consolidated IMU Data Source — Eliminate Redundant SPI Reads

**Priority**: HIGH
**Files**: `tasks/task_imu.c`, `communication/protocol.c`, `drivers/imu_driver.c`

**Description**:
IMU data is read from SPI2 in multiple places:
1. `task_imu` reads calibrated data at 50Hz for attitude calculation
2. `protocol_send_imu_raw_data()` calls `imu_get_all_raw()` — another SPI read
3. `protocol_send_imu_attitude_data()` calls `imu_get_attitude()` — reads from task_imu cache (good)

Reads #1 and #2 can happen concurrently (see BUG-1). Read #2 is also temporally separate from #1, so the raw data sent to ROS 2 doesn't match the attitude data.

**Fix**: Make `task_imu` the sole SPI reader. Cache both raw and calibrated data in thread-safe global structs. Have `protocol_send_*` read from the cache.

**Review**: think and write the best solution for this.

---

### PERF-3: DMA for UART RX

**Priority**: MEDIUM
**File**: `hal/hal_usart.c`

**Description**:
UART receive uses per-byte interrupts (RXNE ISR). At 115200 baud, that's up to ~11,520 interrupts/second. Each interrupt calls `protocol_receive_byte()` and stores in a circular buffer — double work.

**Fix**: Configure DMA1 Channel5 (USART1_RX) with a circular buffer. Process received bytes in bulk from the communication task using `DMA_GetCurrDataCounter()` to detect new data. This eliminates most RX interrupts.

**Review**: think and write the best solution for this.
---

### PERF-4: Odometry Integration — Use Midpoint (RK2) Instead of Euler

**Priority**: LOW
**File**: `control/odometry.c`

**Description**:
Position integration uses simple Euler method:

```c
float delta_x = (vx * cos_theta - vy * sin_theta) * dt;
```

For a robot that rotates while translating (mecanum common case), Euler integration drifts more than midpoint integration, which uses the average of old and new theta:

```c
float mid_theta = odom->theta + delta_theta * 0.5f;
float delta_x = (vx * cosf(mid_theta) - vy * sinf(mid_theta)) * dt;
```

At 100Hz the error per step is small, but it accumulates over time.

**Review**: think deeply and write the best solution for this.

---

### PERF-5: Battery Monitor — Use EMA Filter Instead of Simple Average

**Priority**: LOW
**File**: `drivers/battery_monitor.c`

**Description**:
Battery voltage uses 4 rapid successive ADC reads averaged together. Since there's no delay between samples, they effectively measure the same instant — providing noise filtering but not temporal smoothing.

**Fix**: Use an exponential moving average (EMA) across multiple `battery_get_voltage()` calls:

**Review**: fix it.

```c
static float filtered_voltage = 0.0f;
float raw = /* single ADC read */;
filtered_voltage = 0.9f * filtered_voltage + 0.1f * raw;
```

This smooths transient dips (e.g., motor inrush current) that could cause false low-voltage warnings.

---

## 8. Code Quality & Refactoring Ideas

### REFACT-1: Encoder Direction Mapping — Use Table Instead of Switch

**File**: `drivers/encoder_driver.c`

**Current**: 4-way switch statement with hardcoded direction inversions.

**Better**:
```c
static const int8_t encoder_direction[4] = { -1, 1, 1, -1 };  // Configurable

int16_t encoder_read_delta(uint8_t encoder) {
    if (encoder >= 4) return 0;
    int16_t delta = hal_timer_read_encoder_delta(encoder);
    return delta * encoder_direction[encoder];
}
```

This is cleaner, self-documenting, and easier to configure at runtime (via flash storage).

**Review**: okay do it.

---

### REFACT-2: Motor-to-Timer Mapping — Use Table-Driven Approach

**File**: `hal/hal_timer.c`

**Current**: `hal_timer_set_motor_pwm()` has a 4-way switch with hardcoded timer register accesses and per-motor direction inversion.

**Better**: Define a motor-timer mapping struct:

```c
typedef struct {
    volatile uint32_t *ccr_fwd;  // CCR register for forward PWM
    volatile uint32_t *ccr_rev;  // CCR register for reverse PWM
    int8_t direction;             // +1 or -1 for inversion
} motor_hw_map_t;

static const motor_hw_map_t motor_map[4] = {
    { &TIM8->CCR1, &TIM8->CCR2, -1 },  // M1 FL inverted
    { &TIM8->CCR3, &TIM8->CCR4, -1 },  // M2 BL inverted
    { &TIM1->CCR4, &TIM1->CCR1,  1 },  // M3 FR normal
    { &TIM1->CCR2, &TIM1->CCR3,  1 },  // M4 BR normal
};
```

Reduces code duplication, makes hardware changes a config change.

**Review**: okay do it.

---

### REFACT-3: Remove `extern` Declarations Inside Function Bodies

**Files**: `hal/hal_usart.c`, `drivers/imu_driver.c`

**Current**:
```c
// In hal_usart.c USART1_IRQHandler():
extern void protocol_receive_byte(uint8_t byte);

// In imu_driver.c imu_get_attitude():
extern void imu_task_get_attitude(float *roll, float *pitch, float *yaw);
```

**Better**: Add proper `#include "protocol.h"` and `#include "task_imu.h"` at the top of the file. In-body `extern` declarations bypass the header system and won't catch signature changes.

**Review**: okay do it.

---

### REFACT-4: Consolidate Double GPIO Initialization for Motor Pins

**Files**: `hal/hal_gpio.c`, `hal/hal_timer.c`

**Description**: Motor PWM GPIO pins are initialized as `AF_PP` in both `hal_gpio_init_motor_pwm_pins()` and `hal_timer_pwm_init()`. The second initialization overwrites the first.

**Fix**: Remove GPIO init from `hal_timer_pwm_init()` (it's redundant since `hal_gpio_init()` runs first), or remove from `hal_gpio.c` and keep it collocated with the timer setup.

**Review**: okay do it.

---

### REFACT-5: `flash_storage.h` Comment Says "XOR Checksum" but Implementation Uses Additive

**File**: `include/flash_storage.h`, `drivers/flash_storage.c`

**Description**:
```c
// flash_storage.h line 42:
uint8_t checksum;  // XOR checksum over all preceding bytes  <-- WRONG

// flash_storage.c uses:
sum += bytes[i];  // Additive checksum, not XOR
```

**Fix**: Update the comment in `flash_storage.h` to match the implementation: "Additive checksum over all preceding bytes".

**Review**: update comment.

**Status**: ✅ FIXED — Comment updated to "Additive sum checksum over all preceding bytes".

---

### REFACT-6: Remove Legacy/Dead Protocol Function Codes

**File**: `include/protocol.h`

**Description**: Protocol header declares function codes for features that aren't implemented and may never be (Ackerman steering, UART servo, RGB LED, CAN, arm control). These add confusion for maintainers.

**Fix**: Move unimplemented codes to a "reserved/future" comment block, or remove entirely with a note in the changelog.

**Review**: okay do it.

---

### REFACT-7: Inconsistent Error Return Types

**Files**: Multiple

**Description**: Some functions return `int` (0/-1), others return `int8_t`, others return nothing. Battery functions return `int` where `bool` would suffice. IMU functions use `int` returns. There's no unified error code enum.

**Fix**: Define a firmware-wide error enum:

```c
typedef enum {
    ORBI_OK = 0,
    ORBI_ERR_PARAM = -1,
    ORBI_ERR_TIMEOUT = -2,
    ORBI_ERR_HW = -3,
    ORBI_ERR_CHECKSUM = -4,
} orbi_err_t;
```

**Review**: yes, need a error enum. There I don't like robot name specific funtion name, may be another people can use my firmware with same Yahboom ros expansion board. so you give like ROBOT_OK, 

---

### REFACT-8: `imu_delay_ms()` Is Inaccurate and Should Use FreeRTOS Delay Post-Init

**File**: `drivers/imu_driver.c`

**Description**:
`imu_delay_ms()` uses a busy-wait loop calibrated for 72MHz with 12000 iterations per ms. This is:
- Inaccurate (depends on optimization level, instruction pipeline)
- Blocking (wastes CPU during initialization)
- Used only during init (before scheduler), so FreeRTOS vTaskDelay isn't available

The 12000 iteration count gives ~72000 cycles at ~6 cycles/iteration, which is approximately 1ms at 72MHz, but this varies significantly with compiler optimization flags (`-Os` vs `-O0`).

**Fix**: For pre-scheduler init, use a SysTick-based delay or DWT cycle counter for precise timing. Post-scheduler, use `vTaskDelay()`.

**Review**: okay do it.

---

## 9. Testing Gaps

**Review**: HOld the testing gaps for now. You can create hardware-test.md and write there all those test idea. I have already some test script src\orbibot_rosmaster_firmware\tests. but we are improve this later. 

### TEST-1: No Unit Tests for Core Algorithms

**Priority**: HIGH

The following critical algorithms have no unit tests:
- **PID controller**: `pid_calculate_incremental()`, `pid_get_gains_for_speed()`
- **Mecanum kinematics**: `mecanum_inverse_kinematics()`, `mecanum_forward_kinematics()`
- **Odometry integration**: `odometry_update()`
- **Protocol parsing**: `protocol_receive_byte()` state machine, `protocol_calculate_checksum()`

These are pure functions that could be tested on the host (x86) with a simple test harness, without needing hardware.

---

### TEST-2: No Stress Test for Protocol Double-Buffer

**Priority**: MEDIUM

The double-buffer protocol implementation (primary/secondary buffers, drop counting) has never been stress-tested with:
- Back-to-back packets with no gap
- Packets arriving during auto-report TX
- Maximum-length packets
- Corrupted packets (bad checksum, truncated length)

---

### TEST-3: No Watchdog Recovery Test

**Priority**: MEDIUM

There's no test that verifies the watchdog actually resets the MCU when:
- `task_control` hangs (infinite loop)
- `task_imu` blocks on SPI (hardware failure)
- FreeRTOS heap exhaustion (no tasks can run)

---

### TEST-4: No Flash Storage Wear/Corruption Test

**Priority**: LOW

Flash storage (`flash_storage_save()`) erases and rewrites a page. No test verifies:
- Behavior after thousands of writes (flash endurance ~10K cycles)
- Recovery from power loss during erase/write
- Behavior when flash checksum is corrupted

---

## 10. Previously Resolved (Preserved)

### ✅ Issue #4: Flash Storage Checksum — VERIFIED
Additive checksum implemented in `flash_storage.c`. Covers magic, PID gains, and mag calibration.

### ✅ Issue #5: Watchdog from task_control — FIXED
Added `hal_watchdog_feed()` in `task_control.c` at 100Hz for redundant watchdog feeding (see SAFE-5 for architectural concern).

### ✅ SPI2 Timeout Protection (December 2025)
All SPI operations include timeout loops to prevent infinite blocking.

### ✅ FreeRTOS Task Stack Sizes (January 2026)
Communication task stack increased from 256 to 512 words.

### ✅ Magnetometer DRDY Handling (February 2026)
Last-valid-reading cache prevents zero-value spikes.

---

## Summary Priority Matrix

### Bugs & Code Issues

| ID | Category | Severity | Effort | Description |
|----|----------|----------|--------|-------------|
| BUG-1 | Concurrency | CRITICAL | Medium | SPI2 race between task_imu and task_communication |
| BUG-2 | Config | CRITICAL | Trivial | FreeRTOS hook macros missing — hooks never called |
| BUG-3 | Protocol | HIGH | Low | Drop mode uses stale packet length |
| PROTO-1 | Communication | HIGH | Medium | printf/protocol TX share USART1 — packet corruption |
| SAFE-3 | Safety | MEDIUM | Low | Battery critical doesn't lock out motor commands |
| PROTO-2 | Safety | MEDIUM | Trivial | Angular velocity clamp doesn't match config |
| CFG-3 | Build | MEDIUM | Low | Implicit function declaration warnings suppressed |
| BUG-4 | Config | MEDIUM | Trivial | IMU_UPDATE_RATE_HZ defined twice |
| RACE-1 | Concurrency | MEDIUM | Trivial | IMU attitude writes unprotected |
| SAFE-4 | Safety | MEDIUM | Trivial | No bounds check on motor/encoder index |

### Documentation vs Code Mismatches

| ID | Severity | Description |
|----|----------|-------------|
| DOC-MISMATCH-1 | MEDIUM | Version: README=v2.0.0, code=v1.0.0 |
| DOC-MISMATCH-2 | HIGH | SPI Mode: docs=Mode 3, code=Mode 0 |
| DOC-MISMATCH-3 | HIGH | Checksum: hardware-doc=XOR, code=additive sum |
| DOC-MISMATCH-4 | MEDIUM | CommTask priority: docs=9, code=7 |
| DOC-MISMATCH-5 | MEDIUM | IMU stack: docs=256w, code=1024w |
| DOC-MISMATCH-6 | LOW | Monitor rate: README=10Hz, code=1Hz |
| DOC-MISMATCH-7 | MEDIUM | Battery ADC: README=PC2, code=PC4 |
| DOC-MISMATCH-8 | HIGH | IMU raw report: docs=0x0E, code=0x0B |
| DOC-MISMATCH-9 | LOW | OLED: docs=I2C1, code=software I2C PA2/PA3 |
| DOC-MISMATCH-10 | LOW | Monitor stack: docs=128w, code=512w |
| DOC-MISMATCH-11 | LOW | Architecture dir tree doesn't match files |
| DOC-MISMATCH-12 | LOW | Flash map shows bootloader offset not used |

### Performance & Testing

| ID | Category | Severity | Effort | Description |
|----|----------|----------|--------|-------------|
| PERF-1 | Performance | HIGH | High | Fixed-point PID for no-FPU MCU |
| PERF-2 | Performance | HIGH | Medium | Consolidate IMU data reads |
| PERF-3 | Performance | MEDIUM | Medium | DMA for UART RX |
| TEST-1 | Testing | HIGH | Medium | No unit tests for core algorithms |

---

*Last updated: 2026-03-04*
