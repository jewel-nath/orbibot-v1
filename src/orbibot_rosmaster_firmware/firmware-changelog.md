# OrbiBot Firmware Changelog

All notable changes to the OrbiBot ROSMaster firmware.

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

*Last updated: 2026-03-10*