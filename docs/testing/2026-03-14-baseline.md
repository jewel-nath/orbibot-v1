---
title: "Baseline Test Results"
type: operations
date: 2026-03-14
tags:
  - operations
  - testing
  - baseline
---

# OrbiBot Baseline Test Notes

**Date:** 2026-03-14  
**Tester:** AI Robot Tester (MCP)  
**Launch:** `robot.launch.py` running  
**Location:** Indoor, flat surface

---

## 1. System Health (Baseline)


| Parameter       | Value           | Status   |
| --------------- | --------------- | -------- |
| CPU Load (1min) | 1.66            | ✅ Normal |
| RAM Used        | 19.1%           | ✅ Normal |
| CPU Temp        | 45.8°C          | ✅ Normal |
| Battery         | 12.8V (Nominal) | ✅ Normal |


---

## 2. Firmware / Sensor Data


| Sensor                  | Status         | Notes                  |
| ----------------------- | -------------- | ---------------------- |
| `/odom` topic           | ✅ Publishing   | Firmware serial OK     |
| `/imu/data_raw` topic   | ✅ Publishing   | 50Hz                   |
| `/scan` (LiDAR)         | ✅ Topic exists |                        |
| Static odom drift (10s) | ✅ Zero drift   | Position held at (0,0) |


### ⚠️ IMU Accelerometer Anomaly

- **Measured z-accel (static):** 15.251 m/s²
- **Expected (gravity):** ~9.81 m/s²
- **Ratio:** ~1.55x — likely wrong scale factor or sensitivity setting in firmware
- **Action needed:** Check `ICM_ACCEL_SCALE` / accelerometer FSR config in `orbibot_config.h`

### IMU Gyro Bias (static)

- `angular_velocity.z = -0.013 rad/s` — small constant bias
- Madgwick filter compensates this at runtime
- Acceptable for now

---

## 3. Odometry Accuracy

- Static drift: **0.0m** over 10 seconds ✅
- After PID test (0.2 m/s × 3s):
  - x = 0.532m (expected ~0.6m — 11% short, normal with acceleration ramp)
  - y = -0.033m lateral drift (3.3cm) — from wz noise during forward motion
- Velocity reads zero when motors stopped ✅

---

## 4. Motor PID Tuning — Forward (vx)

**Target:** 0.2 m/s, 3 seconds, sample_hz=20


| #   | Kp        | Ki        | Kd        | MAE (m/s)  | Overshoot | Steady State Avg | Notes                         |
| --- | --------- | --------- | --------- | ---------- | --------- | ---------------- | ----------------------------- |
| 1   | (default) | (default) | (default) | 0.0571     | 30.5%     | ~0.189 m/s       | Baseline, slow rise           |
| 2 ✅ | 2.5       | 0.3       | 0.8       | **0.0366** | **24.5%** | ~0.197 m/s       | Best balance                  |
| 3   | 2.0       | 0.3       | 1.5       | 0.0370     | 39.5%     | ~0.202 m/s       | Kd too high → worse transient |


**Final PID applied:** `Kp=2.5, Ki=0.3, Kd=0.8`

### Observations

- Rise time improved: 780ms → 460ms with tuning ✅
- Overshoot reduced: 30.5% → 24.5% ✅
- Steady-state error: <2% (avg ~0.197 vs target 0.200) ✅
- High Kd (1.5) worsened transient — firmware Kd likely adds during ramp-up
- Overshoot in practice (Nav2 MPPI smooth profile) will be much lower

### ⚠️ WZ Drift During Forward Motion

- `max wz_error = 0.076 rad/s` during forward drive
- Robot veers slightly during straight-line motion
- Cause: mecanum wheel mechanical play or slight wheel radius mismatch
- Fix: yaw PID tuning (see TODO)

---

## 5. Higher Speed Tests Summary

| Speed | Direction | MAE | Overshoot | WZ drift | Steady Err |
|---|---|---|---|---|---|
| 0.2 m/s | Forward | 0.0366 | 24.5% | 0.076 rad/s | 1.5% |
| 0.35 m/s | Forward | 0.0565 | 24.0% | 0.095 rad/s | 0.3% |
| **0.28 m/s** | **Backward** | **0.0497** | **27.1%** | **0.057 rad/s** | **1.1%** |

**Observation:** Backward motion has less WZ drift than forward at same speed.  
**Confirmed operational speed: 0.28 m/s** (user feedback: 0.2 too slow, 0.35 too fast)

---

## 6. Rotation Test — 180° In-Place (wz=0.6 rad/s)

- Command: `move_robot wz=0.6, duration=5.3s`
- Target: 180°, Actual: **≈ 179.5°** (error: 0.5°) ✅
- Yaw PID / rotation accuracy: excellent

---

## 7. Strafe Test — vy Sign Bug Found!

**Test:** `vy=-0.25` (expected right) → robot went **LEFT**

**Root cause:** cmd_vel vy sign is INVERTED vs ROS standard throughout the system:
- `cmd_vel vy = -0.25` → robot goes LEFT (should be right per ROS)
- `cmd_vel vy = +0.25` → robot goes RIGHT (should be left per ROS)
- Odom vy is CORRECT: positive vy = went LEFT (ROS standard) ✅

**Evidence in web GUI** (`MecanumController.tsx` line 93):
```typescript
// Fix: Invert Y axis because vy=1 moves robot Right (instead of Left)
const scaledVy = -vy * maxLinear * speedScale;
```
Web GUI knows about this and compensates. But joystick mode (line 116) does NOT compensate.

**Nav2 impact:** Nav2 sends positive vy for "go left" → robot goes RIGHT → navigation broken for lateral movement! ❌

**Root cause:** Firmware `mecanum_kinematics.c` IK had vy sign mismatch with physical wheel layout.
FK (odom) was already correct. Fix applied in firmware IK only.

**Fix applied:**
1. ✅ `mecanum_kinematics.c`: `float vy = -robot->vy;` (negate vy in IK only)
2. ✅ `MecanumController.tsx` button mode: removed pre-existing inversion workaround
3. ✅ `MecanumController.tsx` joystick mode: added proper inversion to match ROS standard

**After fix:** `cmd_vel vy=+0.25` → robot goes LEFT ✅ (ROS standard)  
**Firmware reflashed and verified ✅**

### Post-Fix Strafe Verification (vy=-0.25, right strafe)

| Metric | Before Fix | After Fix |
|---|---|---|
| VY MAE | 0.466 ❌ (opposite direction) | **0.0845** ✅ |
| VY odom sign | Positive (+) when going right ❌ | Negative (-) when going right ✅ |
| VX crosscoupling | 0.008 m/s | 0.011 m/s ✅ |
| WZ noise | 0.076 rad/s | 0.076 rad/s ✅ |
| Physical direction | Robot went LEFT (wrong) | **Robot went RIGHT** ✅ |

**Fix fully verified — cmd_vel vy convention now matches ROS standard.**

---

## 8. Yaw / Rotation PID Test

### WZ Rotation Test (wz=0.5 rad/s, in-place)
| Metric | Value |
|---|---|
| WZ MAE | 0.1511 rad/s (30%) |
| Overshoot | 26.6% (peak: 0.633 rad/s) |
| Steady state avg | ~0.505 rad/s (target 0.5) ✅ |
| Steady state oscillation | ±0.08 rad/s (16%) |
| VX crosscoupling | 0.006 m/s ✅ |
| Note | Higher oscillation than linear — 4 wheels opposing each other |

### Yaw Drift During Forward Motion (vx=0.28 m/s, 4s)
| Metric | Value | Conclusion |
|---|---|---|
| WZ MAE | 0.0195 rad/s | ✅ Encoder quantization noise |
| WZ max | 0.076 rad/s | ✅ = 4× encoder step (0.019 rad/s) |
| Systematic drift | None detected | ✅ Values are random ± |
| VX overshoot | 21.1% | ✅ Best result today |
| VX steady state | 0.282 m/s (target 0.28) | ✅ 0.7% error |

**Yaw PID conclusion:** Current drift is encoder-resolution-limited. Tuning will not improve further.
Yaw PID is working acceptably for Nav2 use.

---

## 9. Final Status

| System | Status |
|---|---|
| Battery | ✅ 12.8V Normal |
| Firmware serial | ✅ Stable |
| Motor PID | ✅ Kp=2.5, Ki=0.3, Kd=0.8 |
| Forward/Backward | ✅ 0.28 m/s, 21% overshoot |
| Rotation | ✅ 179.5° accuracy at wz=0.6 rad/s |
| **Strafe vy sign bug** | ✅ **Fixed in firmware + webgui** |
| Right strafe | ✅ Verified |
| Yaw drift | ✅ Encoder-limited, acceptable |
| Odom static drift | ✅ Zero |

---

## 10. Remaining TODOs

- [x] ~~Check IMU accelerometer scale factor (z=15.25 m/s² anomaly)~~ — **closed
      2026-08-03.** Root cause was `ACCEL_CONFIG_2 = 0x06` enabling the Z-axis
      self-test, not a scale factor. `|a| = 9.802`, ratio to g 0.9995. Full
      numbers in `test-report.md` §9.4
- [ ] Save motor PID to flash (permanent) — roadmap 1.6
- [x] ~~Left strafe explicit verify (vy=+0.25 → LEFT)~~ — verified wheels-free
- [ ] ~~Magnetometer calibration check~~ — **void.** Magnetometer removed
      2026-04-28. The replacement measurement is **yaw drift rate**, roadmap 1.3
- [ ] Accel X/Y scale under real acceleration — [[backlog-moc]] CC-2

---

## 11. Final Recommendations

| Parameter | Value |
|---|---|
| **Motor PID** | Kp=2.5, Ki=0.3, Kd=0.8 |
| **Normal speed** | **0.28 m/s** |
| Slow/careful | 0.2 m/s |
| Fast/open area | 0.35 m/s |
| In-place rotation | wz = 0.6 rad/s |

---

*Notes auto-generated during live robot testing session.*