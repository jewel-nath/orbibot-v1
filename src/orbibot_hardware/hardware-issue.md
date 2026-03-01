# OrbiBot Hardware Package — Known Issues & Technical Debt

**Last Updated:** 2026-03-01  
**Package Version:** 3.3.9  
**Status:** All critical bugs fixed. Minor technical debt remains.

---

## Issue Summary

| Issue ID | Severity | Status | Description |
|----------|----------|--------|-------------|
| HW-001 | Low | Open | System monitor topic naming convention inconsistency |
| HW-002 | Low | Open | `psutil` dependency not declared in `package.xml` |
| HW-003 | Info | Open | `reset_odometry` service doesn't support custom pose |
| HW-004 | Info | Open | IMU calibration service returns "not supported" |
| HW-005 | Info | Open | No rate limiting on PID parameter topics |

---

## Detailed Issues

### HW-001: System Monitor Topic Naming Convention

**Severity:** Low  
**File:** `system_monitor.py`

**Current Behavior:**
```python
# Publishes to (without /orbibot/ prefix)
'/system_status_enriched'
```

**Expected Behavior:**
```python
# Should follow convention
'/orbibot/system_status_enriched'
```

**Impact:** Minor - breaks topic naming convention but doesn't affect functionality.

**Workaround:** None needed - topic works correctly.

**Fix Required:**
- Update `system_monitor.py` line 18
- Update all subscribers (webgui, etc.)

---

### HW-002: Missing `psutil` Dependency

**Severity:** Low  
**File:** `package.xml`

**Issue:** `system_monitor.py` imports `psutil` but it's not declared as a dependency.

**Current `package.xml`:**
```xml
<exec_depend>orbibot_msgs</exec_depend>
<exec_depend>sensor_msgs</exec_depend>
<!-- Missing: psutil -->
```

**Fix Required:**
```xml
<exec_depend>python3-psutil</exec_depend>
```

**Workaround:** Manually install:
```bash
pip install psutil
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

### HW-005: No Rate Limiting on PID Topics

**Severity:** Info  
**Files:** `hardware_node.py` (PID callbacks)

**Current Behavior:** Every PID topic message is sent to firmware immediately.

**Risk:** Rapid topic spam could overwhelm serial communication.

**Example:**
```bash
# This would send 1000 PID updates per second!
ros2 topic pub -r 1000 /orbibot/pid_params ...
```

**Mitigation:** None currently. Firmware handles it gracefully (serial bandwidth limited).

**Recommended Fix:** Add throttling in callbacks:
```python
# Add rate limiting
if time.time() - self._last_pid_update < 0.1:  # Max 10Hz
    return
```

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
1. Fix HW-001 (topic naming) when convenient
2. Add HW-005 rate limiting for robustness
3. Consider implementing HW-003 (custom pose reset) in firmware

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