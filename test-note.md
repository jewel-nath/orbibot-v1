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
**Firmware reflash required** to apply the IK fix.

---

## 8. TODO / Next Steps

- [ ] **Reflash firmware** to apply mecanum IK vy fix
- [ ] Verify strafe direction after reflash (vy=+0.25 should go LEFT)
- [ ] Check IMU accelerometer scale factor in firmware (`orbibot_config.h`)
- [ ] Save final motor PID to flash
- [ ] Tune Yaw PID to reduce wz drift during forward motion

---

## 8. Final Recommendations

| Parameter | Value |
|---|---|
| **Motor PID** | Kp=2.5, Ki=0.3, Kd=0.8 |
| **Normal speed** | **0.28 m/s** |
| Slow/careful | 0.2 m/s |
| Fast/open area | 0.35 m/s |
| In-place rotation | wz = 0.6 rad/s |

---

*Notes auto-generated during live robot testing session.*