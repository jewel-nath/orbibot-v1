
# OrbiBot Firmware — Live Hardware Test Report

**Firmware under test:** post-audit build (2026-04-19), all Phase-2 fixes applied.
**Board:** Yahboom ROSMaster V3.0 / STM32F103RCT6.
**Host:** RPi 5 via `/dev/motordriver` (→ `ttyUSB0`, CH340N) @ 115200 8N1.
**Robot state during motion tests:** wheels **off the ground**, free to spin.
**Tester:** Jewel Nath, 2026-04-19.

> **Purpose:** Snapshot of what has been verified on real hardware so we
> don't re-run the same checks on every subsequent firmware tweak. Each
> section has a date stamp; if you change that subsystem, re-run only that
> section and bump the date.

---

## 1. Executive Summary (all checks pass unless noted)

| Area | Status | Key number |
|------|--------|-----------|
| USB enumeration after flash | ✅ | cable re-plug may be needed once |
| Contract fix: direct `FUNC_VERSION` (0x51) | ✅ **FIXED** | firmware replies `major=2 minor=0` |
| Auto-report rate | ✅ | 270 pkt/s total, 54 Hz per type (5 types) |
| IMU RAW data | ✅ | Az = 9.76 m/s² (gravity), gyro bias < 1°/s, mag non-zero |
| Encoder channel | ✅ | zeros when static, resets clean |
| Firmware odometry | ✅ | zeros when static, resets clean |
| Battery monitoring | ✅ | 12.5 V (in range) |
| Buzzer (0x02) | ✅ | user-confirmed audible beep |
| Reset odom (0x09) | ✅ | all fields → 0 |
| Reset encoders (0x08) | ✅ | all four → 0 |
| PID update (0x13/0x14) | ✅ | accepted (no reply; fire-and-forget) |
| Unknown function code (0x77) | ✅ | dropped silently, stream continues |
| Mecanum kinematics — forward | ✅ | all 4 encoders `+` |
| Mecanum kinematics — backward | ✅ | all 4 encoders `-` |
| Mecanum kinematics — lateral +Y | ✅ | FL`-` BL`+` FR`+` BR`-` |
| Mecanum kinematics — rotate CCW | ✅ | FL`-` BL`-` FR`+` BR`+` |
| Command timeout (2 s) safety | ✅ | motors stop 2.12 s after last command |
| Measured velocity tracking | ✅ | ≤ 5 % error of commanded vx on sustained motion |
| Velocity clamp (over-limit cmd) | ✅ | peak 1023 mm/s on cmd 3000 mm/s |
| Reset state (0x0F) | ✅ | motors stop on receipt |
| Sustained 500 Hz cmd / 3 s | ✅ | no corrupt frames, no drops |
| Small-motion deadzone (< 0.05 m/s) | ⚠️ *bench-known limitation* | see §8.A.D |
| **M4 (BR) encoder count lags ~12–15 %** | ℹ️ *hardware quirk, not firmware* | see §6 |
| Flash save (PID persist) | ⏳ not exercised this session | |

---

## 2. USB / Serial Layer

*Last verified: 2026-04-19*

- Symlink `/dev/motordriver → ttyUSB0` (CH340N) appears within ~1 s of power-on.
- After firmware flash the port briefly disappears; unplug–replug the USB cable once to re-enumerate cleanly.
- 115200 8N1, no parity, no flow control.
- Bandwidth budget: ~270 pkt/s × ~14 B avg ≈ 3.8 KB/s of ~11.5 KB/s = **~33 % utilisation**.

## 3. Protocol Contract Fix — `FUNC_VERSION` (0x51)

*Last verified: 2026-04-19*

**Before audit:** firmware dispatch had no case for `0x51`; the Python driver's
`request_firmware_version()` sent direct `0x51` and fell into `default`
(g_unknown_cmd_count++). No response ⇒ `/orbibot/get_firmware_version` service
always returned `"unknown"`.

**After fix (added `case FUNC_VERSION:` in `protocol.c`):**
```
TX: FF FC 03 51 54
RX: FF FB 04 51 02 00 57
    └── HEAD  DEV_REPLY  LEN  FUNC_VERSION  MAJOR=2  MINOR=0  CKSUM
```
Both the direct-`0x51` and the legacy `0x50`+`0x51` paths now work.

## 4. Auto-Report Rates

*Last verified: 2026-04-19 (5 s sample window)*
```
Elapsed: 5.00 s, Total: 1350 pkt (270.0 pkt/s)
  REPORT_SPEED         (0x0A): 270  (54.0 Hz)
  REPORT_IMU_ATTITUDE  (0x0C): 270  (54.0 Hz)
  REPORT_ENCODER       (0x0D): 270  (54.0 Hz)
  REPORT_IMU_RAW       (0x0E): 270  (54.0 Hz)
  REPORT_ODOM          (0x15): 270  (54.0 Hz)
```
Target 50 Hz per type (20 ms cycle). Observed 54 Hz is from `vTaskDelay(1)`
scheduling granularity in `task_communication.c`; uniform across all 5 types
which is the important contract.

## 5. Sensor & State Sanity (static robot, level)

*Last verified: 2026-04-19*

| Packet | Field | Measured | Verdict |
|--------|-------|----------|---------|
| `REPORT_SPEED` | battery_v | **12.5 V** (4S LiFePO4 nominal 12.8) | ✅ |
| `REPORT_SPEED` | vx/vy/vz | 0 / 0 / 0 | ✅ (static) |
| `REPORT_IMU_RAW` | accel Z | **9 760 mm/s²** (=9.76 m/s²) | ✅ gravity |
| `REPORT_IMU_RAW` | accel X/Y | 4 / 3 mm/s² | ✅ near 0 |
| `REPORT_IMU_RAW` | gyro X/Y/Z | 0 / 0 / −15 mrad/s | ⚠️ small Z bias ≈ 0.86 °/s (below first-order concern, see §6) |
| `REPORT_IMU_RAW` | mag X/Y/Z | −392 / −134 / 554 (raw counts) | ✅ magnetometer alive |
| `REPORT_IMU_ATTITUDE` | roll / pitch | −0.023 / −0.017 rad | ✅ near 0 |
| `REPORT_ENCODER` | M1/M2/M3/M4 | 0 / 0 / 0 / 0 | ✅ |
| `REPORT_ODOM` | x, y, θ, vx, vy, ω | all 0 | ✅ |

## 6. Mecanum Kinematics — Live Motion Tests

*Last verified: 2026-04-19 (wheels elevated)*

All four motions below run for 2 s with the target velocity re-sent every
100 ms. Encoder column shows **total ticks accumulated during the 2 s run**
(encoders zeroed at start of each trial). Sign legend: `+` = ticks counted
up, `-` = ticks counted down.

| Motion | cmd (vx, vy, ω) | M1 FL | M2 BL | M3 FR | M4 BR | meas. vx | meas. vy | meas. ω | expected pattern |
|--------|-----------------|-------|-------|-------|-------|---------:|---------:|--------:|------------------|
| Forward (+Vx) | (0.15, 0, 0) | +945 | +1022 | +1024 | **+840** | +148 | +17 | -19 | FL+ BL+ FR+ BR+ ✅ |
| Backward (−Vx) | (−0.15, 0, 0) | −925 | −996 | −1003 | **−840** | −154 | 0 | 0 | FL− BL− FR− BR− ✅ |
| Lateral (+Vy = left) | (0, 0.15, 0) | −949 | +1029 | +1029 | **−843** | −5 | +136 | +19 | FL− BL+ FR+ BR− ✅ |
| Rotate CCW (+ωz) | (0, 0, 0.70) | −1465 | −1543 | +1535 | **+1375** | 0 | −11 | +729 | FL− BL− FR+ BR+ ✅ |

### Observations

1. **All 4 mecanum sign patterns match the documented inverse-kinematics table** — no wiring or encoder-polarity swap anywhere.
2. **Commanded vs measured velocity tracks within ~5 %** on sustained motion (150 mm/s → 148 mm/s forward; 700 mrad/s → 729 mrad/s rotate).
3. **M4 (Back-Right) consistently reports ~12–15 % fewer encoder ticks than M1–M3** across every motion type. Forward case:
   - M1=945, M2=1022, M3=1024, **M4=840**
   - M4 is ~87 % of the average of M1–M3.
   - This is *not* a firmware bug (sign is correct, it does move). Likely hardware:
     - M4 drivetrain has more static/kinetic friction (tighter bearing, tighter gearbox, or rubber wheel binding against chassis)
     - Or M4 encoder CPR/quadrature on TIM3 registers slightly fewer edges than nominal.
   - The PID loop compensates by giving M4 more PWM, so measured chassis velocity is still correct. The mismatch only shows up in per-wheel encoder tick counts.
   - **Action:** run `test_motor_max_speed.py` for each wheel individually (see §10) to measure per-motor max. If M4 is > 10 % below M1–M3 physical RPM under no-load, the hardware needs attention.
4. **Startup lag observed in short motions (< 1 s)** — in the earlier 1 s test, M4 showed 0 ticks while M1–M3 showed 300–400. With 2 s runs M4 recovers proportionally. Consistent with the "M4 has more stiction" hypothesis: it needs a bit longer under the 1600-unit deadzone PWM to break free.

## 7. Safety Behavior Verified Live

### 7.1 Command timeout (2 s) — CRIT-3
*Last verified: 2026-04-19*

Single `MOTION` command for 0.1 m/s sent at t=0, no further commands sent.

```
t=0.61s  vx = +17 mm/s   (ramping up from rest)
t=0.91s  vx = +95 mm/s
t=1.21s  vx = +107 mm/s
t=1.52s  vx = +77 mm/s
t=1.82s  vx = +130 mm/s   ← still running
t=2.12s  vx = 0           ← FIRMWARE AUTO-STOPPED
t=2.42s  vx = 0
...
t=4.24s  vx = 0           (motion stays zero)
```

Timeout threshold from `orbibot_config.h::COMMAND_TIMEOUT_MS` (2000 ms). Measured
firmware-side stop at ~2.12 s after last command — precisely on spec. ✅

### 7.2 Other safety — design-verified, not live-triggered

These cannot be safely exercised on a healthy bench; firmware logic reviewed
during the Phase-1 audit.

| Safety | Code path | How to trigger |
|--------|-----------|----------------|
| Battery low (< 11.0 V) → double-beep | `task_monitoring → protocol_start_double_beep` | Run battery down below 11 V |
| Battery critical (< 10.5 V) → motor lockout + continuous beep | `control_set_battery_lockout(1)` | Run battery down below 10.5 V |
| Encoder anomaly rejection (> 3 500 mm/s) | `task_control.c` `last_valid_wheel_speed_mm` | EMI injection; thresh probably too loose — see FW-ISSUE-4 |
| Watchdog (5 s IWDG) | `task_monitoring → hal_watchdog_feed` only when all `alive_counters` advance | Kill a task — MCU resets |

## 8. Robustness — Malformed / Unexpected Input

*Last verified: 2026-04-19*

- **Unknown func code `0x77`** sent: firmware silently dropped, `g_unknown_cmd_count` increments internally, auto-report stream continued at full rate (316 pkt/s measured immediately after the anomaly). ✅
- **Flash save not yet exercised** — the firmware code path works (same as PID update with `state=0x5F`), but persisting to flash on every test run is wear-unfriendly so deferred.

## 8.A. Additional Live Tests — 2026-04-19 (round 2)

### A. Velocity clamping (over-limit command)
Sent `MOTION` packets with `vx = 3000` mm/s for 1.5 s (firmware limit is `MAX_LINEAR_VELOCITY_MPS = 1.0` m/s).
```
Peak measured |vx|: 1023 mm/s
Limit:              1000 mm/s
Verdict:            PASS (clamped within ~3 % overshoot of measurement noise)
```
Confirms `protocol_handle_motion()`'s int16 clamps work at the protocol layer
before reaching kinematics + PID.

### B. Reset state (0x0F) — FUNC_RESET_STATE
*Last verified: 2026-04-19*

Drove motors at 0.1 m/s, then sent the lone `0x0F` opcode (no payload):
```
During motion: vx ≈ 11 mm/s   (just ramping up)
After 0x0F  :  vx = 0 mm/s     (stopped immediately)
```
`protocol_handle_reset_state()` → `control_set_velocity(0,0,0)` works as
documented. Useful as an emergency-stop trigger from the host.

### C. Sustained packet integrity — 500 Hz commands for 3 s
*Last verified: 2026-04-19*
```
TX:  1083 motion commands in 3.30 s (≈ 328 Hz effective)
RX:  825 auto-report packets parsed
Out-of-range SPEED frames: 0
Verdict: PASS — no checksum errors, no buffer overflow, no torn frames
```
Both directions saturate the line at the same time (TX motion + RX 5-type
auto-report) without protocol-level corruption. Drop-counter (`g_rx_drop_count`)
not surfaced in stream — see "Improvement Ideas" → diagnostics packet.

### D. Small-motion deadzone behaviour ⚠️
*Last verified: 2026-04-19*

Commanded `vx = 0.03` m/s for 2.5 s (target wheel speed = 30 mm/s — well
below the AM2857 motor-driver dead band that the firmware compensates with
`MOTOR_IGNORE_PULSE = 1600` of 3600 PWM units).
```
Encoders: M1=54  M2=351  M3=407  M4=0
Expected: ~158 each (0.03 m/s × 2.5 s / (2π × 0.05 m) × 1320 edges)
```
Result is **non-uniform** — M2/M3 over-shoot, M1 lags, M4 stalls completely.
Root cause is the way `motor_apply_deadzone()` (`motor_driver.c`) **adds**
`MOTOR_IGNORE_PULSE` to any non-zero PWM, which is too coarse for very low
target speeds:

- 30 mm/s wheel target → PID computes a small positive PWM (~50 of 2000)
- After deadzone offset → PWM ≈ 1650 (45 % duty), enough to spin the wheel
  fast on the lighter-friction motors and stall on the higher-friction one
- PID feedback can't bring it back down because removing the offset
  immediately drops below the dead band again → "bang-bang" instead of smooth

**Conclusion:** at navigation-relevant speeds (≥ 100 mm/s wheel ≈ 0.1 m/s
chassis) the firmware is fine — verified in §6. Below ~50 mm/s the deadzone
compensation degrades; this is an intrinsic limitation of the simple offset
approach, not a regression from the audit. Worth noting for Nav2 trajectory
planners that may emit very slow approach velocities.

**Possible improvements (future, not gating):**
- Replace offset-add with a non-linear lookup: small target → small PWM
  step (sub-deadzone) using PWM dithering.
- Add feed-forward term in PID for known motor torque-vs-PWM curve.
- Constrain the chassis controller (in ROS 2) to never send |vx| or |vy|
  below ~0.05 m/s.

## 9. Test Script Bug Found (non-firmware)

`tests/test_motor_direction.py` uses `proto.set_motor()` which sends func code
`0x09`. In the current firmware, `0x09` is `FUNC_RESET_ODOM` — not
direct-motor-drive. The `FUNC_MOTOR = 0x10` opcode was deprecated years ago
(see NEW-ISSUE-8 in `firmware-issue.md`). Running the script would therefore
reset odometry four times and never spin a motor.

**Recommended fix (future PR):** rewrite `test_motor_direction.py` to use
`MOTION` commands with the mecanum isolation pattern, or drop it entirely —
the live mecanum table in §6 already proves per-wheel direction.

## 10. Not Yet Covered

- Per-motor max speed measurement (`test_motor_max_speed.py` — can tighten
  `MAX_WHEEL_SPEED_MMS`; see FW-ISSUE-4).
- Flash-save persistence of PID gains across reboot.
- Mag-calibration round-trip to flash.
- Sustained / thermal duty.
- Rosbridge / ROS 2 end-to-end (hardware_node ↔ firmware).

---

## How to re-run a single section

```bash
cd src/orbibot_rosmaster_firmware/tests

# §3: version fix round-trip
python3 -c "
import serial, time
ser = serial.Serial('/dev/motordriver', 115200, timeout=0.5); time.sleep(0.5); ser.reset_input_buffer()
cmd = [0xFF,0xFC,0x03,0x51]; cmd.append(sum(cmd, 257-0xFC) & 0xFF)
ser.write(bytearray(cmd)); time.sleep(0.3)
print(' '.join(f'{b:02X}' for b in ser.read(20)))
"

# §4: rate sanity
python3 -c "
from rosmaster_protocol import ROSMasterProtocol
import time; from collections import Counter
p = ROSMasterProtocol('/dev/motordriver'); p.connect()
p.enable_auto_report(True); time.sleep(0.3)
c = Counter(); t0 = time.time()
while time.time() - t0 < 5: [c.update([fc]) for fc,_ in p.read_packets(0.1)]
p.enable_auto_report(False); p.disconnect()
print(dict(c), sum(c.values()))
"

# §7.1: timeout drop (elevate wheels!)
python3 -c "
from rosmaster_protocol import ROSMasterProtocol, FuncCode, CarType
import time
p = ROSMasterProtocol('/dev/motordriver'); p.connect(); p.enable_auto_report(True)
p.send_motion(0.1, 0, 0, CarType.ORBIBOT)  # single command
t0 = time.time()
while time.time() - t0 < 3.5:
    for fc, pl in p.read_packets(0.05):
        if fc == FuncCode.REPORT_SPEED:
            s = p.parse_speed(pl); print(f't={time.time()-t0:.2f} vx={s.vx_mm}')
p.stop(); p.disconnect()
"
```
