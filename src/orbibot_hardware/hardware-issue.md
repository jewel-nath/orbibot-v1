# OrbiBot Hardware Package — Known Issues & Technical Debt

**Last Updated:** 2026-03-01  
**Package Version:** 3.3.9  
**Status:** All critical bugs fixed. Minor technical debt remains.

---

## Issue Summary

| Issue ID | Severity | Status | Description |
|----------|----------|--------|-------------|
| HW-001 | Low | **Fixed** | System monitor topic naming convention already correct (`/orbibot/system_status_enriched`) |
| HW-002 | Low | **Fixed** | `psutil` dependency declared in `package.xml` |
| HW-003 | Info | Open | `reset_odometry` service doesn't support custom pose (firmware limitation) |
| HW-004 | Info | Open | IMU calibration service returns "not supported" (ICM-20948 auto-calibrates) |
| HW-005 | Info | **Fixed** | Rate limiting added to PID parameter topics (max 10Hz) |

---

## Detailed Issues

### HW-001: System Monitor Topic Naming Convention ✅ FIXED

**Severity:** Low  
**File:** `system_monitor.py`

**Status:** Already correct — topic is `/orbibot/system_status_enriched` as per convention.

**Verification:** The topic name follows the `/orbibot/` prefix convention and matches the webgui expectations.

---

### HW-002: Missing `psutil` Dependency ✅ FIXED

**Severity:** Low  
**File:** `package.xml`

**Status:** Fixed in `package.xml`:
```xml
<exec_depend>python3-psutil</exec_depend>
```

---

### HW-003: Reset Odometry Doesn't Support Custom Pose

**Severity:** Info  
**File:** `hardware_node.py` (line ~460)

**Current Behavior:**
```python
def _reset_odometry_callback(self, request, response):
    # Firmware always resets to (0, 0, 0)
    # request.reset_pose field is ignored
    self.bot.reset_odometry()
    response.message = "Reset to zero only - custom pose not supported"
```

**Expected Behavior:** Support custom pose reset like:
```python
request.reset_pose.position.x = 5.0  # Should reset to x=5.0
```

**Impact:** Low - most use cases reset to origin.

**Reason:** Firmware limitation - `FUNC_RESET_ODOM` (0x09) doesn't accept parameters.

**Workaround:** Software offset tracking in higher-level nodes.

---

### HW-004: IMU Calibration Returns "Not Supported"

**Severity:** Info  
**File:** `hardware_node.py` (line ~445)

**Current Behavior:**
```python
def _calibrate_imu_callback(self, request, response):
    response.success = False
    response.message = "IMU calibration not supported - ICM-20948 auto-calibrates"
    return response
```

**Reason:** ICM-20948 performs automatic calibration on startup. Manual calibration not implemented in firmware.

**Impact:** None - auto-calibration is sufficient for most use cases.

**Workaround:** Power cycle to trigger re-calibration.

---

### HW-005: No Rate Limiting on PID Topics ✅ FIXED

**Severity:** Info  
**Files:** `hardware_node.py` (PID callbacks)

**Status:** Fixed - Rate limiting implemented (max 10Hz per topic).

**Implementation:**
```python
# Rate limiting for PID topics (HW-005)
self._pid_rate_limit = 0.1  # Max 10Hz (100ms between updates)
self._last_pid_update = 0.0
self._last_yaw_pid_update = 0.0
self._last_pid_multilevel_update = 0.0
self._last_pid_save_update = 0.0
```

Applied to all PID callbacks:
- `_pid_callback()` - `/orbibot/pid_params`
- `_yaw_pid_callback()` - `/orbibot/yaw_pid_params`
- `_pid_multilevel_callback()` - `/orbibot/pid_multilevel`
- `_pid_save_callback()` - `/orbibot/pid_save`

---

## Fixed Issues (Historical Reference)

These issues were found and fixed in previous audits:

| Issue | Description | Fix |
|-------|-------------|-----|
| BUG-1 | Lock held during serial write causing cmd_vel blocking | Release lock before `set_car_motion()` |
| BUG-2 | Serial reconnect didn't restore auto-report | Re-send `set_auto_report_state()` after reconnect |
| Q1 | Dead code `_limit_motor_value` | Removed |
| Q2 | No explicit `close()` method | Added `close()` method |
| Q3 | Magic number `car_type=7` | Use `CARTYPE_ORBIBOT` constant |
| C1 | Flash writes on every startup | Use `forever=False` |
| C2 | Missing `covariance_decay` in YAML | Added parameter |
| HW-001 | System monitor topic naming | Already correct |
| HW-002 | Missing psutil dependency | Added to package.xml |
| HW-005 | No rate limiting on PID topics | Added 10Hz rate limiting |

---

## Technical Debt

### Code Organization
- **File Size:** `rosmaster_driver.py` (520 lines) - acceptable but could split protocol constants to separate file
- **Function Length:** Some functions in `hardware_node.py` exceed 50 lines - could refactor for readability

### Documentation
- **Inline Comments:** Good coverage but some complex math sections could use more explanation
- **Docstrings:** All public methods documented, some private methods lack docstrings

### Testing
- **Unit Tests:** No formal unit tests for protocol parsing
- **Integration Tests:** Relies on manual testing with actual hardware

### Performance
- **Memory:** No memory leaks detected, but `last_firmware_odom` cache grows unbounded (stores only latest)
- **CPU:** Sensor callback at 50Hz is appropriate, could optimize if needed

---

## Recommendations

### For Beginners
1. **Install psutil manually** if system monitor fails to start
2. **Expect reset_odometry to always reset to (0,0,0)** regardless of request
3. **Power cycle for IMU re-calibration** instead of using service

### For Developers
1. ✅ HW-001 - Topic naming already correct
2. ✅ HW-002 - psutil dependency added
3. ✅ HW-005 - Rate limiting implemented
4. Consider implementing HW-003 (custom pose reset) in firmware if needed

---

## How to Report New Issues

If you find a bug:

1. Check this file first
2. Run diagnostic script:
   ```bash
   python3 scripts/comprehensive_diagnostic.py
   ```
3. Check logs:
   ```bash
   ros2 node logs /orbibot_hardware_node
   ```
4. Create detailed report with:
   - Error message
   - Steps to reproduce
   - Expected vs actual behavior
   - Hardware/firmware version

---

## Related Documentation

- [README.md](README.md) - Usage and API reference
- [hardware-changelog.md](hardware-changelog.md) - Development history
- [FIRMWARE_ARCHITECTURE.md](../orbibot_rosmaster_firmware/FIRMWARE_ARCHITECTURE.md) - Firmware details

---

**End of Issues Document**