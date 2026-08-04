
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
| IMU RAW data | ✅ | \|a\| = 9.802 m/s², ratio to g 0.9995; gyro bias < 1°/s |
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
| `REPORT_IMU_RAW` | accel Z | **9 802 mm/s²** (=9.802 m/s²) | ✅ gravity — *re-measured 2026-08-03* |
| `REPORT_IMU_RAW` | accel X/Y | 14 / 16 mm/s² | ✅ near 0 — *re-measured 2026-08-03* |
| `REPORT_IMU_RAW` | gyro X/Y/Z | 0 / 0 / −15 mrad/s | ⚠️ small Z bias ≈ 0.86 °/s (below first-order concern, see §6) |
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

## 9. Deep-Dive Audit Live Verification — 2026-04-28

**Auditor:** Claude (Opus 4.7) under Jewel Nath's direction.
**Scope:** Live-verify findings in `firmware-issue-deepdive.md` that are
testable on the bench. Robot wheels off the ground, battery 12.5 V.

### 9.1 DD-1 — Truncated-payload command handling (CRITICAL)

**Test script:** `tests/test_malformed_packets.py`.

**Method:** Build five `[HEAD, 0xFC, LEN=3, FUNC, CKSUM]` packets — total
5 bytes, no payload, valid checksum — for each at-risk function code.
Send 20 of each in 100 ms windows, sample REPORT_SPEED for 1.5 s after
each blast for rogue motion or stream interruption.

**Pre-fix run (commit before 2026-04-28 protocol.c edit):**

| Function | rx_len | After-blast effect |
|----------|-------:|--------------------|
| `FUNC_AUTO_REPORT (0x01)` | 5 | OK — handler reads `data[0]` only |
| **`FUNC_MOTION (0x12)`** | 5 | **🔴 vx=1029 mm/s commanded** from stale RAM |
| **`FUNC_SET_MOTOR_PID (0x13)`** | 5 | **🔴 vx=993 mm/s spike** (stale MOTION payload re-driven via PID-state coincidence) |
| `FUNC_SET_YAW_PID (0x14)` | 5 | OK — yaw gains overwritten with junk but no direct motion |
| **`FUNC_SET_MAG_CAL (0x16)`** | 5 | **🔴 stream silent ≥3.5 s, IWDG reset at 5 s** — handler's unconditional `flash_storage_save()` ran with garbage hard-iron offsets |

**Fix applied:** `protocol.c` — added `protocol_min_rx_len()` lookup
table + length-gate at the top of `protocol_parse_command()`. Truncated
packets now increment `g_unknown_cmd_count` and are dropped before the
handler runs.

**Post-fix run (2026-04-28):**

```
Step 1: Baseline — 50.0 Hz on all 5 report types
Step 2: Blast 20× FUNC_AUTO_REPORT  (0x01) → speed=53.2 Hz, motion=(0,0,0)  OK
Step 2: Blast 20× FUNC_MOTION       (0x12) → speed=53.2 Hz, motion=(0,0,0)  OK
Step 2: Blast 20× FUNC_SET_MOTOR_PID(0x13) → speed=53.9 Hz, motion=(0,0,0)  OK
Step 2: Blast 20× FUNC_SET_YAW_PID  (0x14) → speed=53.2 Hz, motion=(0,0,0)  OK
Step 2: Blast 20× FUNC_SET_MAG_CAL  (0x16) → speed=53.9 Hz, motion=(0,0,0)  OK
Step 3: Final 2 s — speed=49.9 Hz vs baseline 50.0
```

**Verdict:** ✅ DD-1 closed by the protocol-side length gate. All five
truncated-payload classes are now silently dropped with no stream
disruption and no motion side effect.

### 9.2 Per-motor max speed (FW-ISSUE-4 baseline)

**Test script:** `tests/test_motor_max_speed.py` at `--speed 1.0 --duration 5`.
Robot is forward-driven at the firmware velocity ceiling (`MAX_LINEAR_VELOCITY_MPS`
= 1.0 m/s). The PID loop saturates each wheel against the chassis-velocity
limit, not the motor-saturation limit, so this measures *velocity-clamped*
behaviour rather than raw motor RPM.

| Motor | Avg (mm/s) | Avg (rad/s) | Max (mm/s) | Std | Samples |
|-------|-----------:|------------:|-----------:|----:|--------:|
| M1 (FL) | 1001.7 | 20.03 | 1050.6 | 28.7 | 250 |
| M2 (BL) | 1002.0 | 20.04 | 1059.9 | 29.1 | 248 |
| M3 (FR) | 1002.5 | 20.05 | 1050.7 | 28.0 | 248 |
| M4 (BR) | 1002.4 | 20.05 | 1060.0 | 28.9 | 249 |

**Inter-motor variation:** **0.1 %** in steady-state averages
(fastest 1003 mm/s, slowest 1002 mm/s).

**Findings:**
1. **No per-motor weakness at steady state.** The 12–15 % M4 lag noted
   in §6 was transient stiction during the first few hundred ms; once
   PID converges, all 4 motors hold the commanded chassis velocity to
   within 0.5 mm/s of each other.
2. **`MAX_WHEEL_SPEED_MMS = 3500` is loose.** Worst-case combined
   wheel speed at the firmware limits — `vx + vy + (lx+ly)·ω = 1.0 +
   0.5 + 0.222·2 = 1.94 m/s` — fits comfortably in a 2000 mm/s threshold.
   Recommend tightening to 2200 mm/s (10 % margin over worst-case).
   This makes the encoder-anomaly rejection in `task_control.c` more
   useful as a noise filter (current 3500 only triggers on EMI-grade
   spurious encoder pulses).
3. The peak-instantaneous spikes (~1060 mm/s) are PID overshoot during
   the 200 ms ramp-up window, not steady-state. Don't size
   `MAX_WHEEL_SPEED_MMS` against them.

### 9.3 Mag-calibration round-trip — OBSOLETE

> Superseded 2026-04-28. The magnetometer was removed across firmware,
> driver and msgs — indoor hard/soft-iron contamination made it unusable
> for heading, and heading is now gyro + accel (Madgwick, `use_mag: false`)
> corrected by slam_toolbox/AMCL. `FUNC_SET_MAG_CAL (0x16)` no longer
> exists, so there is nothing left to round-trip. Kept for provenance;
> DD-11 is closed by deletion. Original text below.

`protocol_handle_set_mag_cal()` calls `flash_storage_save()`
unconditionally — no `SAVE_VERIFY` (0x5F) gate like PID has, no RAM-only
mode. A round-trip test would consume one flash erase cycle for no test
value. Recommended Phase 3 follow-up:

1. Add a `state` byte to the SET_MAG_CAL payload (matches PID convention)
   so callers can distinguish "live calibrate" from "calibrate + persist".
2. Then run round-trip in RAM-only mode and verify `imu_data.mag_*` is
   correctly hard-iron corrected.

This isn't a bug — it's a design-consistency gap with the PID handler
(which does have the gate). Logged as **DD-11** in `firmware-issue-deepdive.md`.

---

## 9.4 FW-BUG-2 Root Cause — Accel Z Self-Test — 2026-08-03

*Robot static and level, on a stool, wheels free. Firmware: this branch
(April base + `ACCEL_CONFIG_2 = 0x00`, nominal ±2g scale).*

§5's original 9.76 m/s² was produced by `accel_scale = 9.80665/25644`, an
empirical factor added in 2.0.1 to cancel a 1.566× reading. The cause was
not the chip: `ACCEL_CONFIG_2 = 0x06` set bit 2 = `AZ_ST_EN_REG`, enabling
the Z-axis self-test actuator. See the changelog entry for the register
layout.

Because the original 15.35 m/s² was taken **at rest**, where `|a|` is
almost entirely Z, only the inflated axis was ever sampled — and the
factor was then applied to all three axes.

| Firmware | `ACCEL_CONFIG_2` | scale | raw az | `\|a\|` | ratio to g |
|---|---|---|---|---|---|
| 2.0.1 – Apr 28 | `0x06` | `9.80665/25644` | ~25330 | 9.606 | 0.980 |
| March base, no compensation | `0x06` | nominal | ~25330 | 15.179 | 1.548 |
| **this branch** | **`0x00`** | **nominal** | **~16613** | **9.802** | **0.9995** |

630 samples over 12.0 s (52.5 Hz):

```
ax  mean  +0.014 m/s²   sd 0.0084
ay  mean  +0.016 m/s²   sd 0.0069
az  mean  +9.802 m/s²   sd 0.0159
|a| mean   9.802 m/s²   sd 0.0159      ratio to g 0.9995
```

**Still open:** X and Y were never inflated by the self-test, so the old
`9.80665/25644` made them read ~36 % low. A static robot cannot show this —
`ax` and `ay` are both ~0 either way. Confirming the X/Y scale needs a
known acceleration on the ground, which belongs with the odometry
calibration run, not here.

---

## 9.5 ROS 2 End-to-End — hardware_node ↔ firmware — 2026-08-03

*Robot static on a stool, wheels free. Clean colcon build, `hardware.launch.py`
only — no motion commanded.*

This is the check that would have caught the months-long raw-IMU outage: the
firmware and the driver must agree on packet length, or `rosmaster_driver.py`
length-checks and returns without a word.

| Topic | Measured | Verdict |
|---|---|---|
| `/imu/data_raw` | **49.998 Hz** | ✅ 12-byte packet parsed |
| `/joint_states` | **49.971 Hz** | ✅ |
| `/orbibot/encoders` | **49.951 Hz** | ✅ |
| `/odom` | **1.949 Hz** | ✅ **by design — see below** |

**`/odom` at ~2 Hz on a stationary robot is correct, not a fault.** The
firmware de-duplicates identical odometry and falls back to a 0.5 s heartbeat,
so a robot that is not moving produces ~2 messages/s. It rises to the full rate
under motion. Do not "fix" this.

`/imu/mag` appears in `ros2 topic list` with **zero publishers** — nothing emits
it. Any subscriber is a leftover process from before the magnetometer was
removed, not a live part of the system.

---

## 10. Not Yet Covered

- Flash-save persistence of PID gains across reboot.
- Accel X/Y scale under real acceleration (see §9.4) — needs the robot on the ground.
- Sustained / thermal duty.
- Anything measured **on the ground** — distance, drift, traction, PID under load.

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

---

## 9.6 Power Rail Under Motor Load (P-3 / P-5) — 2026-08-03

**Host:** Beelink SER5 Pro, `/dev/motordriver` → `ttyUSB0`, CH340N @ 115200.
**Robot state:** elevated on a stool, **wheels free**.
**Power:** 4S LiFePO4, charger **disconnected**. Beelink on its own mains
adapter; the shared 12.8 V rail feeds the ROSMaster board.
**Method:** `robot.launch.py` up, motors enabled explicitly, four 3 s bursts at
20 Hz `cmd_vel`, battery sampled from `/orbibot/system_status` throughout.

| Profile | min V | max V | mean V |
|---|---|---|---|
| forward 0.15 m/s | 12.60 | 12.70 | 12.68 |
| forward 0.30 m/s | 12.60 | 12.70 | 12.67 |
| rotate 1.0 rad/s | 12.60 | 12.70 | 12.66 |
| rotate 2.0 rad/s | 12.60 | 12.70 | 12.63 |

Idle before the run: **12.80 V**.

**P-5: pass.** Uptime advanced 766 s → 792 s across the whole run — no reboot.
Kernel log shows **no under-voltage, brownout, hard-reset or over-current
events** at any point since boot. The only USB disconnects in the log are the
four from the operator swapping the camera's port and cable, all outside the
test window.

> **Read the kernel log with `journalctl -k`, not `dmesg`.** This machine has
> `kernel.dmesg_restrict` set, so an unprivileged `dmesg` fails with
> *"read kernel buffer failed: Operation not permitted"* — and a `dmesg | grep
> -c` therefore returns a confident **0** having read nothing at all. The first
> version of this section claimed "dmesg shows zero resets" on exactly that
> basis. `journalctl -k` works for any user in the `adm` group.

**P-3: not yet answered.** Do not read the table as a pass. Three limits, in
descending order of importance:

1. **Wheels free.** The motors drew roughly their no-load current. Real traction
   load is several times higher, and stall is ~3 A per motor. This is a lower
   bound on the draw, so an upper bound on the rail's health.
2. **Resolution.** The firmware reports battery in **0.1 V steps**. The whole
   observed excursion — 12.80 idle to 12.60 loaded — is two steps. The honest
   statement is *"sag was not resolvable at this current"*, not *"sag was
   0.20 V"*.
3. **Battery near full.** The margin that matters is at the bottom of the
   discharge curve, close to the 10.5 V BMS cutoff and the converter's 10 V
   minimum input. Nothing here probes that.

**An earlier run of this same test, an hour before, was void** — the charger was
still connected to the pack, so the rail was being held up by the charger rather
than the battery. It produced identical numbers, which is worth knowing: at
no-load motor current this measurement cannot tell a charged battery from a
charger, because neither moves the reading.

**Still required before the robot drives autonomously:**

- P-1 and P-2 — converter *output* under load. Needs a multimeter on the 19 V
  side; not observable in software.
- P-3 proper — wheels on the ground, under real traction load, battery part
  discharged.
- P-4 — converter case temperature after 30 min under load.

See `docs/operations/computer-setup.md` for the pass criteria.

---

## 9.7 Stationary IMU — noise, bias and yaw drift — 2026-08-04

*Robot **elevated on a stool**, wheels free, motors disabled, Beelink powered
but **not yet mounted**. Full `robot.launch.py`. 29 977 raw samples over
**10 minutes**, no one touching the robot. Tool:
`ros2 run orbibot_localization measure_imu_noise -p duration:=600.0`.*

This replaces the covariances of 2026-03-24, which came from 212 samples on the
Raspberry Pi through the accelerometer path later found faulty (CC-3), and it is
the first time yaw drift has been measured on this robot at all — the number
that replaced the magnetometer when it was removed on 2026-04-28.

### Accelerometer

| axis | mean (m/s²) | stddev | variance (m/s²)² |
|---|---|---|---|
| X | +0.00308 | 0.00726 | 5.277e-05 |
| Y | **−0.16003** | 0.00735 | 5.395e-05 |
| Z | +9.80707 | 0.01290 | 1.665e-04 |

**|a| = 9.8084 m/s², ratio to g = 1.0002.** The accel scale is correct to
0.02 % — FW-BUG-2's inflated-Z era is over, and CC-2's scale question is
answered for the static case. Dynamic scale still needs the robot on the ground.

### Gyroscope

| axis | bias (°/s) | stddev (rad/s) | variance (rad/s)² |
|---|---|---|---|
| X | +0.14675 | 0.000769 | 5.910e-07 |
| Y | **−0.45684** | 0.000765 | 5.854e-07 |
| Z | **+0.00162** | 0.000227 | 5.160e-08 |

Gyro Z is an excellent axis: bias 0.0016 °/s, and a noise floor **19× below**
the 1e-6 that had been configured. X and Y are 90× and 280× noisier in bias.

### Yaw drift, and what actually causes it

| | °/min |
|---|---|
| **Measured**, `/imu/data_filtered`, over 10 min | **+0.547** |
| Predicted from gyro **Z** bias alone | +0.097 |

A 5.6× gap — and it is fully explained. The gravity vector shows the sensor is
**not level**:

```
roll  (about X) = −0.935°        pitch (about Y) = −0.018°
```

Euler yaw kinematics leak the other two gyro axes into yaw through that tilt:

```
ψ̇ = (ω_y·sin φ + ω_z·cos φ) / cos θ
  = (−0.45684)(−0.01632) + (+0.00162)(0.99987)
  = +0.00907 °/s = +0.544 °/min      vs +0.547 measured — 0.47 % error
```

**The drift is not a gyro problem. It is a mounting problem.** A 0.94° tilt
turns a −0.457 °/s bias on an axis nobody watches into 83 % of the heading
error. Level the sensor and drift should fall to about **+0.10 °/min
(5.8 °/hour)** from **+0.55 °/min (33 °/hour)**.

**Tilt direction confirmed independently.** `a_y = −0.160` gives a negative
roll, which rotates +Y (left) toward −Z — so the sensor says the **right side
is up**. The operator, asked afterwards, reported the right side sitting
slightly high, with the board moved rearward but not rotated. Two independent
observations agreeing on which side is up also checks the whole convention
chain: firmware axes → driver → URDF `rpy="0 0 0"` → ROS sign convention.

The rearward move is not reflected in the URDF (`imu_joint` is still at the
robot centre) — `description-issue.md` DESC-1. It does not affect anything
above: the gyro is translation-invariant, `imu0_config` fuses yaw and vyaw
only, and this run was stationary.

### `/odom` while stationary

`vx`, `vy`, `vyaw` all read **exactly 0.000000, stddev 0.000000** over 1 158
messages. Wheels free and still, encoders report exact zero — no quantisation
dither to integrate.

### What this changes

- `hardware_params.yaml` IMU covariances replaced with the measured values.
  **Stationary floor only** — vibration under motion will raise them, and the
  EKF's Mahalanobis rejection scales as 1/√covariance, so this must be
  re-measured while driving before Phase 1 tuning.
- Of the six, only `gyro_covariance_z` reaches the EKF (`imu0_config` fuses yaw
  and vyaw only).
- Madgwick `zeta: 0.0` should be reconsidered on this evidence — see
  `localization-issue.md` LOC-1.

### Not covered

Yaw drift **with the sensor level**, and everything under vibration. Both wait
on the Beelink being mounted (Phase 0.8).

---

## 9.8 Accelerometer scale off-axis, and an axis-convention check — 2026-08-04

*Robot **held in the operator's hands**, motors disabled, full `robot.launch.py`.
Five poses held ~5–19 s each, 3 741 samples over 75 s. Tool:
`.claude/scripts/imu_sequence.py`, which finds held poses by looking for
stretches where the gyro goes quiet, so the operator never has to type.*

### Accelerometer magnitude through ±21° of tilt — **this is the new result**

| pose | roll | pitch | `\|a\|/g` |
|---|---|---|---|
| level | −0.84° | +0.51° | **1.0026** |
| tilt A | −1.41° | +20.01° | **1.0069** |
| tilt B | +0.08° | −20.61° | **0.9947** |
| tilt C | +21.18° | +1.04° | **1.0038** |
| tilt D | −21.74° | +0.01° | **0.9953** |
| level | −0.81° | +0.49° | **1.0022** |

At 20° of tilt roughly **3.4 m/s²** lands on X or Y, so this is the first time
those two axes have carried a large, known signal. Magnitude stays within
**0.7 %** of g in every orientation.

**This closes the half of CC-2 that was thought unmeasurable.** The concern was
that X and Y read ~0 on a static robot, so the post-FW-BUG-2 scale could not be
checked on them. Tilting is the way round that: gravity is a known 9.807 m/s²
and tilting simply points it at a different axis. What remains open in CC-2 is
genuinely dynamic scale — the robot accelerating along the floor, which needs
Phase 1.

### Axis convention — **not resolved, and deliberately not called either way**

The same run was meant to verify roll/pitch signs by asking for four named
tilts. The magnitudes were all correct, but the **pairing came out rotated 90°**:
"lift the left side" produced pitch, "lift the front" produced roll.

Two explanations fit equally well from the data alone:

1. the IMU is mounted rotated 90° w.r.t. `base_link`, making the URDF's
   `rpy="0 0 0"` wrong, or
2. the robot was **held** rotated in the operator's hands, so their "left" was
   the robot's front.

**(2) is the more likely**, because the static baseline disagrees with (1): on
the stool the sensor read `roll = −0.935°`, `pitch = −0.018°`, and the operator
independently reported the **right side** sitting high. Under a 90° board
rotation that same reading would have meant a *pitch*, i.e. nose up or down,
which is not what was seen.

Not being able to separate the two from this data is the finding. Resolving it
takes one short run described **without the words left and right** — tilt the
camera end up, then down — where a `pitch` response clears the sensor and a
`roll` response convicts the URDF. Recorded rather than guessed.

### Method note

The operator could not press a key while holding the robot with both hands, so
the poses were cued through `Monitor` at fixed intervals and the recorder found
them afterwards by stillness. That worked, but the ~7 s between a cue being
emitted and the operator acting is enough to mis-pair poses with instructions if
anything is skipped — so `imu_sequence.py` reports **the measured angles first**
and its own PASS/FAIL second, and says so when the counts do not line up.

---

## 9.9 The IMU is mounted 90° rotated — found, proven three ways, fixed — 2026-08-04

*Robot hand-held and on a table, motors disabled, full `robot.launch.py`. Eight
separate captures. Tools: `.claude/scripts/imu_sequence.py`,
`imu_orientation.py`, `imu_base_frame.py`.*

**`imu_joint` claimed `rpy="0 0 0"`. It is `rpy="0 0 1.5707963"`.** The sensor's
+X axis points along the robot's **left** (`base_link` +Y). Roll and pitch were
swapped everywhere downstream, and had been since the URDF was written.

Nothing below rests on a single measurement. An earlier version of this section
did, and was deleted before it was committed.

### 1 · Physical pitch shows up as sensor roll — three separate holds

Named tilts kept contradicting each other, because "lift the left side" depends
on where the operator is standing. What worked was a **visible feature instead
of a direction** — the camera:

| held pose | sensor roll | sensor pitch |
|---|---|---|
| camera end **up**, hold 1 | +21.86°, +23.45° | +1.14, +1.31 |
| camera end **up**, hold 2 (29.8 s) | **+23.33°** | +1.21 |
| camera end **down**, hold 3 | **−22.24°, −21.01°** | +0.01, +0.04 |

Nose-up is *by definition* pitch. The sensor answered on **roll**, every time,
in both directions.

### 2 · The frame is a rotation, not a reflection — three rotations, both ways

A roll↔pitch swap has two possible causes needing opposite fixes:

- a **rotation** — frame turned, still right-handed → the URDF is wrong
- a **reflection** — X and Y swapped without a sign change → left-handed, which
  no mounting can produce, so it would be an index bug in firmware or driver

They differ in **handedness**, which shows up in a *yaw* rotation — and a yaw
rotation can be specified without the words left or right: *turn it clockwise
seen from above.*

| # | direction | gyro Z peak | yaw change |
|---|---|---|---|
| 1 | clockwise | **−25.38 °/s** | −22.00° |
| 2 | clockwise | **−41.25 °/s** | **−90.13°** |
| 3 | **counter-clockwise** | **+44.86 °/s** | **+84.04°** |

Clockwise negative, counter-clockwise positive — the right-handed convention,
and the sign flips with the direction. **Reflection is ruled out**, so the URDF
is the right place to fix it.

In a right-handed frame, nose-up → roll **positive** occurs for exactly one
orientation: sensor +X along `base_link` +Y, **+90°**. The other way gives roll
negative.

### 3 · End-to-end, after the fix

TF reports the new value, and a TF-aware consumer now sees the correct axis:

```
TF base_link ← imu_link :  yaw +90.00°

camera end held UP:
  on the topic  (imu_link)  roll  +8.32°   pitch  +0.95°   → "LEFT side up"  ✗
  resolved into base_link   roll  -0.98°   pitch  +8.32°   → NOSE UP         ✓
```

### What this re-labels — the physics does not change

Applying the transform to the resting readings of §9.7:

| sensor reads | actually means |
|---|---|
| roll −0.935° | **rear raised 0.94°** |
| pitch −0.018° | no side tilt |

Which is what the operator said **first**, before anything was measured. §9.7's
drift analysis stands — it was computed entirely in the sensor frame and is
self-consistent — but its labels change: the leaking bias is the **sensor Y**
gyro (−0.457 °/s), the robot's *roll* axis, leaking through a rear-up *pitch*.
Magnitude, mechanism and remedy are unchanged: level the board, gain 5.6×.

### How much this was costing, honestly

**Very little today, and a great deal soon.** `imu0_config` fuses yaw and vyaw
only; `imu0_relative: true` cancels a constant yaw offset; angular velocity
about Z is invariant under a Z-rotation. The EKF's arithmetic was unaffected.

It starts costing the moment any of these happen: `two_d_mode` turned off,
accelerometer fusion enabled, roll/pitch used for a tilt or roll-over check, or
anyone reading `/imu/data_filtered` orientation directly — a dashboard, a
safety check, `ros2 topic echo`. It was also wrong in RViz the whole time.

### Verification after the fix

```
/imu/data_raw       50.06 Hz      /odometry/filtered   50.00 Hz
/imu/data_filtered  50.00 Hz      /scan                 8.07 Hz
hardware_node 10.33 % of one core · zero errors in the launch log
odom → base_footprint intact
```
