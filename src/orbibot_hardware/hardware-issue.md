# OrbiBot Hardware Package — Known Issues

**Last Updated:** 2026-03-06  
**Package Version:** 3.3.9  
**Status:** All must-fix issues are fixed. Remaining items below are **optional** (known limitations or firmware/design).

---

## Optional / Known Limitations

The following are **optional** — no action required unless you need the behavior. Full backlog is in [hardware-changelog.md](hardware-changelog.md).

| Issue ID | Severity | Description |
|----------|----------|-------------|
| HW-003 | Info (optional) | `reset_odometry` service doesn't support custom pose (firmware limitation) |
| HW-004 | Info (optional) | IMU calibration service returns "not supported" (ICM-20948 auto-calibrates) |

---

### HW-003: Reset Odometry Doesn't Support Custom Pose (optional)

**Severity:** Info  
**File:** `hardware_node.py`

- Firmware always resets to (0, 0, 0); `request.reset_pose` is ignored.
- **Reason:** `FUNC_RESET_ODOM` (0x09) doesn't accept parameters.
- **Impact:** Low — most use cases reset to origin.
- **Workaround:** Software offset tracking in higher-level nodes.

---

### HW-004: IMU Calibration Returns "Not Supported" (optional)

**Severity:** Info  
**File:** `hardware_node.py`

- Service returns `success=False`, message: "IMU calibration not supported - ICM-20948 auto-calibrates".
- **Reason:** ICM-20948 auto-calibrates on startup; manual calibration not in firmware.
- **Impact:** None for typical use.
- **Workaround:** Power cycle to trigger re-calibration.

---

## Fixed Issues (Summary)

All must-fix items have been addressed, including:

- **Phase 1–3:** BUG-1 to BUG-5, Q1–Q14, R1–R2, R4–R5, S1–S2, P1, D1, C1–C2, N1, HW-001, HW-002, HW-005.
- **Latest:** Q5 (PID rate-limit helper), R3 (dynamic parameter reconfiguration), R6 (buffered serial reads), S3 (battery recovery log), S4 (motor enable retry), PKG-1/PKG-2 (package/resource files), T1 (unit tests), T2 (launch test).

See [hardware-changelog.md](hardware-changelog.md) for full history.

---

## Recommendations

- **Reset odometry:** Expect (0,0,0) only; custom pose would require firmware change.
- **IMU re-calibration:** Power cycle instead of using the service.

---

## How to Report New Issues

1. Check this file and [hardware-changelog.md](hardware-changelog.md).
2. Run: `python3 scripts/comprehensive_diagnostic.py`
3. Check logs: `ros2 node logs /orbibot_hardware_node`
4. Report: error message, steps to reproduce, expected vs actual, hardware/firmware version.

---

## Related Documentation

- [README.md](README.md) — Usage and API
- [hardware-changelog.md](hardware-changelog.md) — Development history and all fixes
- [FIRMWARE_ARCHITECTURE.md](../orbibot_rosmaster_firmware/FIRMWARE_ARCHITECTURE.md) — Firmware details
