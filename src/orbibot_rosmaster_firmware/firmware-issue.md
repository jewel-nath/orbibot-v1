# OrbiBot Firmware — Issue Tracker & Code Review

**Last reviewed**: 2026-03-18
**All issues resolved**: 2026-03-18
**Firmware version**: v2.0.0

---

## Status: All issues closed

All 15 issues identified in the 2026-03-18 code review have been fixed.

| ID | Severity | Title | Fix |
|----|----------|-------|-----|
| H-3 | High | Encoder direction docstring contradiction | Removed incorrect docstring; file-level comment is authoritative |
| H-4 | High | Velocity ramp allows instant direction reversal | Added sign-change detection before magnitude comparison |
| M-1 | Medium | Vy double-inversion: fragile cross-layer coupling | Added cross-reference comments in both files; double-inversion is intentional and documented |
| M-2 | Medium | `FUNC_SET_MOTOR_PID_MULTILEVEL (0x18)` stub not cleaned up | Removed constant and declaration from `protocol.h`; removed from README |
| M-3 | Medium | VERSION command protocol documentation mismatch | README updated to show correct `0x50+0x51` packet format |
| M-4 | Medium | Monitoring task blocks 600ms during low-battery buzzer | Replaced with non-blocking `protocol_start_double_beep()`; state machine runs in `task_communication` at 1ms |
| M-5 | Medium | `encoder_prev_cnt` race condition during encoder reset | Wrapped `encoder_reset_all()` in `taskENTER_CRITICAL()` / `taskEXIT_CRITICAL()` |
| M-6 | Medium | `g_rx_drop_count` will silently overflow | Added saturation at `UINT32_MAX` |
| M-7 | Medium | [DOC] IMU attitude scale: README says ×1000, code uses ×10000 | README corrected to `int16 × 10000 rad` |
| M-8 | Medium | [DOC] Raw IMU function code: README says 0x0B, code uses 0x0E | README updated to `0x0E REPORT_ICM_RAW`; `FUNC_REPORT_MPU_RAW (0x0B)` removed from `protocol.h` |
| L-1 | Low | Dead code: `g_current_vx/vy/vz` written but never read | Removed all three variables from `protocol.c` |
| L-2 | Low | `task_communication.c` header says "4 data types" but sends 5 | Fixed comment to "5 data types at 20Hz each" |
| L-3 | Low | PID gain validation does not reject NaN or Inf | Added `isfinite()` check in both `control_set_motor_pid` and `control_set_yaw_pid` |
| L-4 | Low | Odometry theta normalization uses while loops instead of fmod | Replaced with `fmodf()` + two `if` statements |
| L-5 | Low | Battery lockout float equality vs zero | Replaced `!= 0.0f` with `fabsf() > 1e-6f` epsilon comparison |

---

## Files changed

| File | Issues fixed |
|------|-------------|
| `src/drivers/encoder_driver.c` | H-3 |
| `src/tasks/task_control.c` | H-4, L-3, L-5 |
| `src/control/mecanum_kinematics.c` | M-1 (documentation) |
| `src/communication/protocol.c` | M-1 (documentation), M-4, M-5, M-6, L-1 |
| `include/protocol.h` | M-2, M-8 |
| `src/tasks/task_monitoring.c` | M-4 |
| `src/tasks/task_communication.c` | M-4, L-2 |
| `src/control/odometry.c` | L-4 |
| `README.md` | M-2, M-3, M-7, M-8 |

---

*This file is maintained alongside active firmware development.*
*Prefix issues with component: `[HAL]`, `[DRV]`, `[CTRL]`, `[PROTO]`, `[TASK]`*
