# OrbiBot Firmware Changelog

All notable changes to the OrbiBot ROSMaster firmware.

---

## v2.0.2 — 2026-03-14 (IMU Debug & Protocol Fix)

### CRIT-3: Protocol Function Code Mismatch (IMU All-Zeros Bug)

**Severity:** CRITICAL  
**Files:** `src/communication/protocol.c`, `src/orbibot_hardware/rosmaster_driver.py`

**Problem**: `protocol_send_imu_raw_data()` was sending IMU packets with function code
`FUNC_REPORT_MPU_RAW` (`0x0B`), but the ROS 2 driver (`rosmaster_driver.py`) only parsed
packets with `FUNC_REPORT_ICM_RAW` (`0x0E`). Every IMU packet was silently dropped on the
host side, producing all-zero accel/gyro data on `/imu/data_raw`. The downstream
`imu_filter_madgwick` reported *"The IMU seems to be in free fall"* because `|a| = 0`.

**Root Cause**: The ROS 2 driver was updated to use the ICM-20948-specific code (`0x0E`)
but the firmware was never updated to match — a cross-layer consistency failure.

**Solution**:  
- `protocol.c` line 568: `FUNC_REPORT_MPU_RAW` → `FUNC_REPORT_ICM_RAW`

**Verification**: Confirmed with verbose boot debug that ICM-20948 hardware was always
functional (WHO_AM_I = 0xEA, PWR_MGMT_1 = 0x41, az ≈ 3155 ADC counts at boot). The problem
was purely in the protocol layer, not hardware.

**Files Modified**:
- `src/communication/protocol.c`: Fixed function code on line 568

---

### DEBUG: IMU Verbose Boot Diagnostics Added

**Severity:** Non-functional (debug tooling)  
**File:** `src/drivers/imu_driver.c`, `include/orbibot_config.h`

Added step-by-step `BOOT_PRINTF` output to `imu_driver_init()` for bench debugging.
Controlled by `ENABLE_BOOT_MESSAGES` in `orbibot_config.h` (default: 0 = production).

**When enabled (`ENABLE_BOOT_MESSAGES = 1`)** the serial monitor shows:
- SPI2 pin mapping confirmation (PB12–PB15)
- PWR_MGMT_1 readback after reset (expect `0x41`)
- WHO_AM_I actual value with chip identification table:
  - `0xEA` → ICM-20948 ✅
  - `0x71` → MPU-9250 (wrong chip)
  - `0x70` → MPU-6500 (wrong chip)
  - `0xFF` → MISO stuck high (SPI/power fault)
  - `0x00` → MISO stuck low (wiring fault)
- First accel sample in raw ADC counts after config (az ≈ 2048 = 1g at ±16g)
- Magnetometer init result
- Gyro calibration completion

**Files Modified**:
- `src/drivers/imu_driver.c`: Verbose debug in `imu_driver_init()`; debug-only code wrapped
  in `#if ENABLE_BOOT_MESSAGES` to avoid `-Werror=unused-variable` in production builds
- `include/orbibot_config.h`: `ENABLE_BOOT_MESSAGES`/`ENABLE_DEBUG_OUTPUT`/`DEBUG_LEVEL`
  restored to `0` for production after debugging session

---

### FIX: ICM-20948 Sensor Scale Ratios Corrected (ROS 2 Driver)

**Severity:** HIGH  
**File:** `src/orbibot_hardware/orbibot_hardware/rosmaster_driver.py`

**Problem**: `ICM20948_ACCEL_RATIO` and `ICM20948_GYRO_RATIO` were both `1/1000.0`,
assuming the firmware sends pre-scaled milli-units. The firmware actually sends raw 16-bit
ADC counts. This caused:

| Sensor | Before | After | Error |
|--------|--------|-------|-------|
| Accel | `1/1000 = 0.001` m/s²/count | `0.004788` m/s²/count | 4.79× under |
| Gyro | `1/1000 = 0.001` rad/s/count | `0.001065` rad/s/count | 6.5% under |
| Mag | `1/1000 = 0.001` µT/count | `0.15` µT/count | 150× under |

**Impact**: Madgwick filter normalized the acceleration vector (direction only), so
orientation estimation was unaffected. However, published `linear_acceleration` values were
physically wrong, and gyro rates had a 6.5% systematic error causing heading drift. Mag
was 150× too small.

**Solution** (ROS 2 side — no firmware reflash required):
```python
ICM20948_GYRO_RATIO  = 2000.0 / 32768.0 * (math.pi / 180.0)  # ±2000 dps → rad/s
ICM20948_ACCEL_RATIO = 16.0   / 32768.0 * 9.80665             # ±16g    → m/s²
ICM20948_MAG_RATIO   = 0.15                                    # AK09916 → µT/count
```

**Files Modified**:
- `src/orbibot_hardware/orbibot_hardware/rosmaster_driver.py`: Added `import math`,
  corrected three `ICM20948_*_RATIO` constants and updated comment

---

## v2.0.1 — 2026-03-10 (Issue Fixes)

### CRIT-2: Protocol Version Response Fixed

**Severity:** CRITICAL  
**File:** `communication/protocol.c`

**Problem**: `FUNC_VERSION` command returned hardcoded `{0x01, 0x00}` instead of actual firmware version from `firmware_version.h`.

**Solution**:
- Added `#include "firmware_version.h"` to `protocol.c`
- Changed version response to use `FIRMWARE_VERSION_MAJOR` and `FIRMWARE_VERSION_MINOR` macros
- Now correctly reports firmware version (e.g., v2.0.0 → `{0x02, 0x00}`)

**Files Modified**:
- `src/communication/protocol.c`: Added version header include, fixed hardcoded version

---

## v2.0.0 — 2026-03-04 (Production Release)

**Theme**: Deep Audit & Hardening — Comprehensive reliability, safety, and code-quality release based on audit vs ROSMaster X3, LGDXRobot2, and AuBot references.

### Summary of Changes

| Category | Count | Key Improvements |
|----------|-------|------------------|
| Critical Bug Fixes | 4 | SPI race condition, FreeRTOS hooks, protocol drops, duplicate defines |
| Concurrency Fixes | 3 | IMU critical sections, encoder atomic reads, RX staging |
| Safety Features | 5 | Fault handlers, HSE fallback, battery lockout, bounds checks, per-task watchdog |
| Protocol Hardening | 4 | Debug gating, velocity clamps, voltage clamps, error counting |
| Performance | 3 | Single SPI reads, RK2 odometry, battery EMA filter |
| Code Quality | 8 | Table-driven dispatch, error enums, DWT delays, documentation fixes |
| Documentation | 12 | All code-vs-doc mismatches resolved |

### Critical Fixes

- **BUG-1**: SPI2 race condition eliminated — `task_imu` sole SPI reader, comm task uses cache
- **BUG-2**: FreeRTOS stack overflow and malloc failed hooks now functional
- **BUG-3**: Protocol drop mode now tracks correct packet length
- **BUG-4**: Duplicate `IMU_UPDATE_RATE_HZ` definition removed

### Safety & Reliability

- HardFault/StackOverflow/MallocFailed use direct USART writes (no heap/printf)
- HSE failure falls back to HSI @ 36MHz (degraded but operational)
- Battery critical state sets `g_battery_lockout` — motors refuse commands until recovery
- Per-task alive counters — watchdog fed only if all tasks report alive
- Bounds checking on all motor/encoder indices

### Performance Improvements

- Odometry: Euler → Midpoint (RK2) integration for reduced rotation drift
- Battery: EMA filter (α=0.3) smooths motor inrush transients
- IMU: Consolidated single-SPI-read via `imu_read_both()`

### Architecture Improvements

- Encoder direction: Table-driven (`const int8_t encoder_direction[4]`)
- Motor PWM: Table-driven (`motor_hw_map_t` with CCR pointers)
- Unified error handling: `robot_err_t` enum across codebase
- DWT cycle-accurate delays (replaced iteration-based busy-wait)

### Documentation Corrections

SPI Mode 0, additive checksum, CommTask priority 7, IMU stack 1024, monitoring 1Hz, battery on PC4, OLED on PA2/PA3, flash at 0x0800_0000 — all 12 doc-vs-code mismatches fixed.

---

## v1.x — 2025-12 to 2026-02 (Development & First Audit)

**Theme**: Initial implementation and first audit hardening.

### First Audit Fixes (2026-02-18)

**Critical**: Battery state machine, IMU thread safety, odometry critical sections  
**High**: BEEP validation, SPI read consolidation, double-buffer checking  
**Medium**: Config constants, buzzer fallback, encoder docs, flash checksum  
**Low**: Derived constants, unified PI, debug levels

### Initial Implementation (2025-11 to 2026-01)

- FreeRTOS with 4 tasks (control 100Hz, IMU 50Hz, comm, monitoring)
- ICM-20948 driver with gyro calibration and magnetometer support
- Multi-level incremental PID with runtime tuning
- Mecanum kinematics (inverse + forward)
- Double-buffered serial protocol (Yahboom-compatible)
- Hardware quadrature encoder counting
- Battery monitoring with 3-level thresholds
- Flash persistence for PID and mag calibration
- PlatformIO build system with `-Werror`

---

## Open Improvements (See firmware-issue.md)

| Priority | Item |
|----------|------|
| HIGH | Fixed-point PID (FPU-less MCU optimization) |
| HIGH | Host-side unit tests |
| MEDIUM | DMA UART RX, encoder EMA filtering |
| MEDIUM | Flash persistence for PID thresholds |
| LOW | Gyro calibration timing, stack monitoring |

---

*Last updated: 2026-03-14*