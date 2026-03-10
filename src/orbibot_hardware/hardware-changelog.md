# orbibot_hardware — Changelog

**Audited:** 2026-03-09 (Deep Analysis vs References)  
**Status:** All must-fix items complete. Production-ready.

---

## v3.4.0 — 2026-03-10 (Issue Fixes)

### Summary of Changes

| Category | Items | Status |
|----------|-------|--------|
| HIGH-1 | Firmware version parsing | ✅ Complete |
| HIGH-2 | IMU calibration service | ✅ Complete |

### HIGH-1: Firmware Version Query Exposure

**Fixed in:** `rosmaster_driver.py`, `hardware_node.py`

**Problem**: Firmware supports `FUNC_VERSION` (0x51) but driver didn't parse or expose it. The `_parse_data` method didn't handle `FUNC_VERSION` responses.

**Solution**:
- Added `FUNC_VERSION = 0x51` constant to rosmaster_driver.py
- Added `_firmware_version` attribute to `Rosmaster` class (initialized to "unknown")
- Added parsing logic in `_parse_data()` to extract version from firmware responses
- Added `get_firmware_version()` getter method to expose version string

**Files Modified**:
- `orbibot_hardware/rosmaster_driver.py`: Added version constant, attribute, parsing, and getter

### HIGH-2: IMU Calibration Service Implementation

**Fixed in:** `hardware_node.py`

**Problem**: Service returned "not supported" but firmware DOES support magnetometer calibration via `FUNC_SET_MAG_CAL` (0x16). The driver already had `set_mag_calibration()` method.

**Solution**:
- Replaced placeholder `_calibrate_imu_callback()` with working implementation
- Service now calls `bot.set_mag_calibration(0.0, 0.0, 0.0)` to trigger calibration
- Supports calibration time parameter for sensor stabilization
- Returns proper success/failure responses with diagnostic messages

**Files Modified**:
- `orbibot_hardware/hardware_node.py`: Implemented `_calibrate_imu_callback()`

---

## Summary

| Phase | Items | Status |
|-------|-------|--------|
| Phase 1 | 9 bugs/quality fixes | ✅ Complete |
| Phase 3 | 18 architecture improvements | ✅ Complete |
| Phase 4 | 9 robustness/testing additions | ✅ Complete |
| v3.4.0 | 2 HIGH priority fixes | ✅ Complete |

**vs References**: OrbiBot hardware is significantly more advanced than Yahboom original and AuBot in safety features, code quality, and architecture.

---

## Critical Fixes (All Complete)

| ID | Issue | Fix |
|----|-------|-----|
| BUG-1 | Lock held during serial write | Moved `set_car_motion` outside `_cmd_time_lock` |
| BUG-2 | Reconnect didn't restore auto-report | Re-enable auto-report after reconnect |
| BUG-3 | Lock in `_motor_enable_callback` | Moved serial call outside `_state_lock` |
| BUG-4 | Wrong packet length | Use `_send_command()` helper with dynamic length |
| BUG-5 | Race in `clear_auto_report_data()` | Removed dead code |

## Architecture Improvements (All Complete)

| ID | Improvement | Impact |
|----|-------------|--------|
| R1 | Single sensor fetch per cycle | ~50% reduction in lock acquisitions |
| R2 | Robot params from YAML | No code changes for wheel/encoder changes |
| R3 | Dynamic parameter reconfiguration | Runtime tuning via `ros2 param set` |
| R4 | IMU covariance from YAML | Tunable without restart |
| R5 | `_send_command()` helper | Consistent, error-proof packet building |
| R6 | Buffered serial reads | Reduced CPU usage on RPi |

## Safety & Robustness (All Complete)

| ID | Feature | Benefit |
|----|---------|---------|
| S1/S2 | Data freshness monitoring | No stale data during disconnect |
| S3 | Battery recovery logging | Clear user guidance |
| S4 | Motor enable at 6s (single call) | Reliable startup, no redundant second call |
| HW-005 | PID rate limiting | Prevents firmware overload |

## Code Quality (All Complete)

- Removed MPU9250 dead code (ICM-20948 only)
- Removed unused constants (FUNC_MOTOR, FUNC_CAR_RUN, etc.)
- Removed legacy `__main__` test block
- Python 3 style class declarations
- DRY PID rate-limiting with helper
- Consistent error handling

## Testing (All Complete)

- `test/test_rosmaster_protocol.py` — Protocol parsing unit tests
- `test/test_launch_hardware.py` — Launch integration tests

## vs Reference Implementations

| Feature | OrbiBot | Yahboom | AuBot |
|---------|---------|---------|-------|
| Safety (cmd timeout, battery lockout) | ✅ Full | ⚠️ Basic | ❌ None |
| Thread safety | ✅ Locks | ❌ None | ❌ None |
| Odometry quality | Firmware RK2 + adaptive | ROS-side Euler | ROS-side Euler |
| Code quality | Clean, typed | Mixed, cluttered | Simple, basic |
| Serial protocol | Binary (robust) | Same | JSON (verbose) |
| Buffered reads | ✅ Yes | ❌ No | ❌ No |
| Dynamic params | ✅ Yes | ❌ No | ❌ No |
| **Firmware version query** | ✅ Yes | ❌ No | ❌ No |
| **IMU calibration** | ✅ Yes | ❌ No | ❌ No |

## Open Improvements (Optional)

See [hardware-issue.md](hardware-issue.md) for optional enhancements:
- MED-1: Encoder direction verification
- MED-2: Enhanced reconnection resilience
- MED-3: Buffer safety limit

---

*Last updated: 2026-03-10*