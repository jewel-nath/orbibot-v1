# OrbiBot — Improvement Plan (from lgdxrobot2 Study)

Reference: `lgdxrobot2` open-source project (ICM-20948, mecanum wheels, STM32F411)
Last updated: 2026-03-23

---

## Full Comparison: OrbiBot vs lgdxrobot2

### Architecture

| Feature | OrbiBot | lgdxrobot2 | কোনটা ভালো |
|---------|---------|-----------|-----------|
| **MCU** | STM32F103RCT6 (72MHz) | STM32F411 (100MHz) | lgdx (faster) |
| **RTOS** | FreeRTOS (4 tasks, priorities) | Bare-metal (timer ISR) | **OrbiBot** (safer) |
| **Communication** | UART 115200 baud (~11.5 KB/s) | USB CDC (~12 Mbps) | **lgdxrobot2** (faster) |
| **Main loop** | 4 FreeRTOS tasks at different rates | Single timer ISR (100Hz all-in-one) | **OrbiBot** (isolated) |
| **Watchdog** | IWDG via task_monitoring | None | **OrbiBot** |
| **ROS2 agent** | Python (rclpy) | C++ (rclcpp) | **lgdxrobot2** (faster) |

### PID & Motor Control

| Feature | OrbiBot | lgdxrobot2 | কোনটা ভালো |
|---------|---------|-----------|-----------|
| **PID type** | Incremental PID | Positional PID | Both valid |
| **PID levels** | Single (all speeds) | 3-level speed-dependent interpolation | lgdx (more flexible) |
| **Per-motor gains** | Same gains for all 4 | Different gains per motor × per level | **lgdxrobot2** |
| **Per-motor max speed** | Assumed uniform | Measured: {12.85, 12.06, 11.74, 10.47} rad/s | **lgdxrobot2** |
| **Anti-windup** | Conditional integral clamp | Back-calculation (undo trapezoidal) | Both good |
| **PID tuning tool** | ROS2 topic-based (`/orbibot/pid_params`) | Qt GUI with real-time chart | **lgdxrobot2** |
| **Flash persistence** | ✅ PID in flash | ✅ PID + mag + max speed in flash | Both |
| **Velocity ramp** | Asymmetric (instant accel, gradual decel) | Symmetric (`MOTOR_SPEED_RAMP=0.1` rad/s/tick) | **OrbiBot** (smoother) |
| **Yaw PID** | ✅ Heading drift compensation from IMU | None | **OrbiBot** |
| **Encoder anomaly filter** | ✅ Discard > MAX_WHEEL_SPEED_MMS | Discard > max_speed (use last valid) | **Both** (now matched) |
| **PID output normalization** | Raw PWM counts | Normalized by max_speed before PWM | lgdx (more portable) |
| **Command timeout** | ✅ CRIT-3 safety stop | None in firmware | **OrbiBot** |

### Odometry

| Feature | OrbiBot | lgdxrobot2 | কোনটা ভালো |
|---------|---------|-----------|-----------|
| **Integration method** | RK2 (midpoint) | Euler | **OrbiBot** (less drift) |
| **Covariance** | Adaptive (grows with distance, decays) | None | **OrbiBot** |
| **Position tracking** | Firmware-side + EKF | Firmware-side + EKF | Both |
| **Heartbeat re-publish** | ✅ (late-joiner support) | No | **OrbiBot** |
| **Deduplication** | ✅ (skip unchanged frames) | No | **OrbiBot** |

### IMU & Sensors

| Feature | OrbiBot | lgdxrobot2 | কোনটা ভালো |
|---------|---------|-----------|-----------|
| **Gyro calibration** | 1000 samples | 500 samples | **OrbiBot** |
| **Accel calibration** | ✅ X/Y bias at startup | X/Y/Z bias + gravity removal | **Both** |
| **Covariance** | ✅ Firmware startup Welford variance + ROS2 script | Firmware rolling 500-sample variance | **OrbiBot** (stationary = correct noise) |
| **Mag calibration** | Python yaml (3 scalars) | Flash (3x3 matrix + ellipsoid fit) | **lgdxrobot2** |
| **Madgwick `zeta`** | 0.001 (drift correction) | 0.0 (none) | **OrbiBot** |
| **Madgwick `orientation_stddev`** | 0.05 (~3°) | 0.0 ("perfect") | **OrbiBot** |
| **EKF frequency** | ✅ 25Hz | 50Hz | lgdx (faster, C++ node) |
| **Firmware attitude** | Complementary filter (debug) | None | **OrbiBot** |

### E-Stop & Safety

| Feature | OrbiBot | lgdxrobot2 | কোনটা ভালো |
|---------|---------|-----------|-----------|
| **Software e-stop** | ✅ | ✅ | Both |
| **Hardware e-stop** | Battery lockout | GPIO pin + DRxSTBY | **lgdxrobot2** (dedicated pin) |
| **Battery low e-stop** | ✅ (critical voltage lockout) | ✅ (separate e-stop type) | Both |
| **Watchdog** | IWDG + task alive kicks | None | **OrbiBot** |
| **Command timeout** | ✅ (configurable) | None | **OrbiBot** |

---

## ✅ Completed (2026-03-23)

| # | Item | Where Fixed | Changelog |
|---|------|------------|-----------|
| 4 | Fix misleading `imu0_relative` comments | `ekf_params.yaml` | `localization-changelog.md` |
| 3 | EKF frequency 15→25Hz | `ekf_params.yaml` | `localization-changelog.md` |
| 5 | Madgwick params → yaml file | `madgwick_params.yaml` + `localization.launch.py` | `localization-changelog.md` |
| 1 | Firmware accel X/Y bias calibration | `imu_driver.c` + `imu_driver.h` | `firmware-changelog.md` |
| 2a | IMU noise measurement script (ROS2 side) | `measure_imu_noise.py` + `setup.py` | `localization-changelog.md` |
| 2b | Firmware startup variance (Welford) | `imu_driver.c` + `imu_driver.h` | `firmware-changelog.md` |
| 11 | IMU topic architecture docs | `hardware/README.md` | `hardware-changelog.md` |
| 12 | Encoder anomaly detection | `task_control.c` + `orbibot_config.h` | `firmware-changelog.md` |

---

## Remaining Items — IMU & Localization

### [MEDIUM] Mag Calibration Architecture — Firmware 3x3 Unused

Python hardware_node applies 3 scalar corrections. Firmware has full 3x3 soft-iron matrix
capability but `mag_cal.calibrated = 0` at boot. `_calibrate_imu_callback` sends (0,0,0).

**Action (staged):**
- Stage 1: Comment cleanup + deprecate confusing `_calibrate_imu_callback` service
- Stage 2: Move correction to firmware, add flash persistence (like lgdxrobot2)

### [MEDIUM] Ellipsoid Fitting for Soft-Iron

`calibrate_magnetometer.py` uses min/max span → 3 diagonal scale factors.
lgdxrobot2 uses Eigen SVD ellipsoid fitting (`fit.cpp`) → full 3x3 matrix.

**Action:** Add `--method ellipsoid` flag using numpy least-squares (AlignedXYEqual mode).

### [MEDIUM] Madgwick `gain` Tuning (test needed)

Both OrbiBot and lgdxrobot2 use `gain: 0.1`. Madgwick paper default is `0.033`.
Mecanum motor vibration may make 0.1 too aggressive for accelerometer trust.

**Action:** Test `gain: 0.05` vs `0.1` on actual robot — compare orientation stability at stop.

### [LOW] Mag Calibration Flash Persistence

lgdxrobot2 stores mag hard-iron + soft-iron in STM32 flash. OrbiBot stores in Python yaml.

### [LOW] Per-axis IMU Covariance

After running `measure_imu_noise`, update `hardware_node.py` to publish per-axis covariance.

---

## Remaining Items — PID & Motor Control (NEW from lgdxrobot2 study)

### [HIGH] Per-Motor Max Speed Measurement

**lgdxrobot2 finding:** তাদের 4 motor এর measured max speed:
```
Motor 0: 12.85 rad/s
Motor 1: 12.06 rad/s
Motor 2: 11.74 rad/s
Motor 3: 10.47 rad/s   ← 23% slower than Motor 0!
```

OrbiBot ধরে নেয় সব motor সমান। কিন্তু JGB37-520 motor গুলোতেও manufacturing variation
থাকবে। Motor max speed না জানলে PID output normalization এবং encoder anomaly rejection
সঠিকভাবে করা যায় না।

**Action:** প্রতিটি motor আলাদাভাবে max PWM দিয়ে max speed measure করো।
```bash
# Proposed test procedure:
# 1. Motor 1 enable, full PWM, measure encoder speed 5 sec → average
# 2. Repeat for motors 2, 3, 4
# 3. Store in orbibot_config.h as MOTOR_MAX_SPEED_M1..M4
```

**Impact:** Encoder anomaly filter, PID tuning accuracy, odometry accuracy.
**Effort:** 30 min test + 10 min config update

### [MEDIUM] PID tuning — Single PID তোমার জন্য যথেষ্ট, কিন্তু সঠিকভাবে tune হওয়া দরকার

**তোমার ধারণা সঠিক:** OrbiBot এর speed range (100-500 mm/s indoor navigation) এ single PID
যথেষ্ট। lgdxrobot2 এর 3-level PID system তাদের wider speed range (2-10 rad/s, ~75-375 mm/s
at their wheel radius) এর জন্য — এটা over-engineering করার দরকার নেই।

**কিন্তু lgdxrobot2 থেকে ২টা জিনিস শেখা যায়:**

1. **PID tuner GUI / real-time chart:** lgdxrobot2 এর chassistuner Qt app এ:
   - Target velocity set করো → real-time motor response graph দেখো
   - Overshoot, settling time, steady-state error visually দেখা যায়
   - P, I, D separately adjust করো live

   OrbiBot এ topic-based PID tuning আছে (`/orbibot/pid_params`) কিন্তু real-time graph নেই।
   `orbibot_webgui` তে একটা PID tuning page যোগ করলে অনেক সহজ হবে।

2. **Step response test procedure:** Systematic PID tuning method:
   ```
   ১. Ki=0, Kd=0 রাখো
   ২. Kp বাড়াও যতক্ষণ না oscillation শুরু হয় (Ku = ultimate gain)
   ৩. Kp = 0.6 * Ku (Ziegler-Nichols)
   ৪. Ki যোগ করো slowly — steady-state error কমাও
   ৫. Kd যোগ করো — overshoot কমাও
   ৬. Real-world test: straight line 1m, 90° turn, figure-8
   ```

**Action:**
- Phase 1: WebGUI তে PID tuning page (step response graph) — orbibot_webgui scope
- Phase 2: Document systematic PID tuning procedure in firmware README

**Effort:** Phase 1: 4-6h (webgui), Phase 2: 30 min doc

### [MEDIUM] PID Output Normalization

**lgdxrobot2 `motor.c:426`:**
```c
pid_output[i] = roundf(((pid_p + pid_i + pid_d) / motor_max_speed[i]) * pwm_counter_max);
```

PID output কে motor max speed দিয়ে normalize করে PWM এ convert করে।
এতে PID gains speed-independent থাকে — motor পরিবর্তন করলেও gains একই থাকে।

**OrbiBot:** PID output সরাসরি PWM count (incremental PID, no normalization)।
Current approach কাজ করছে, কিন্তু gains motor-specific (motor/gear ratio পরিবর্তন করলে re-tune লাগবে)।

**Verdict:** Low priority — current single PID working fine. Consider only if motors are replaced.

### [LOW] Speed Ramp Tuning

**lgdxrobot2:** `MOTOR_SPEED_RAMP = 0.1` rad/s per tick (symmetric, both accel and decel)
**OrbiBot:** `MOTOR_DECEL_RAMP_MMS = 10.0` mm/s per tick (asymmetric — instant accel, gradual decel)

OrbiBot এর asymmetric approach আসলে বেটার — responsive acceleration with smooth deceleration।
lgdxrobot2 এর symmetric ramp acceleration কে ও slow করে দেয়।

**তবে decel rate ঠিক কিনা verify করো:**
- Current: 10 mm/s per 100Hz tick = 1000 mm/s² deceleration
- At 0.5 m/s: stop in 0.5s — reasonable
- At 0.3 m/s (typical indoor nav): stop in 0.3s — good

**Verdict:** No change needed. OrbiBot's asymmetric ramp is better than lgdxrobot2's symmetric.

---

## Remaining Items — Odometry (NEW from lgdxrobot2 study)

### [LOW] Firmware Odometry — Already Better Than lgdxrobot2

**lgdxrobot2 `motor.c:477-479` (Euler integration):**
```c
transform[0] += (vx * cos(theta) - vy * sin(theta)) * dt;
transform[1] += (vx * sin(theta) + vy * cos(theta)) * dt;
transform[2] += (omega * dt);
```

**OrbiBot `odometry.c:42-48` (RK2 midpoint integration):**
```c
float mid_theta = odom->theta + delta_theta * 0.5f;  // ← midpoint trick
float delta_x = (vx * cosf(mid_theta) - vy * sinf(mid_theta)) * dt;
```

RK2 তে rotation + translation simultaneous হলে drift কম। lgdxrobot2 এর Euler method
circular arc motion এ significant error দেয়। OrbiBot already better — no change needed.

---

## OrbiBot Advantages Summary (no change needed)

| Feature | Why OrbiBot is better |
|---------|----------------------|
| `orientation_stddev: 0.05` | lgdxrobot2 uses 0.0 — tells EKF "perfect IMU" (wrong) |
| `zeta: 0.001` | lgdxrobot2 uses 0.0 — no gyro drift correction at all |
| `imu0_relative: true` | Safer for indoor SLAM — no startup jumps |
| FreeRTOS 4-task isolation | lgdxrobot2 single bare-metal ISR — less robust |
| Watchdog (IWDG) | lgdxrobot2 has none |
| Command timeout (CRIT-3) | lgdxrobot2 has no timeout safety |
| 1000 gyro calibration samples | lgdxrobot2 uses 500 |
| IMU driver error handling | WHO_AM_I, timeouts, retries — lgdxrobot2 has none |
| RK2 odometry integration | lgdxrobot2 uses basic Euler — more drift |
| Adaptive odometry covariance | lgdxrobot2 sends none |
| Asymmetric velocity ramp | lgdxrobot2 symmetric ramp slows acceleration |
| Yaw PID heading compensation | lgdxrobot2 has no yaw control |
| Odometry deduplication + heartbeat | lgdxrobot2 sends every frame regardless |

---

## Priority Summary

| Priority | Item | Category | Effort |
|----------|------|----------|--------|
| **HIGH** | Per-motor max speed measurement | PID/Motor | 30 min test |
| **MEDIUM** | Mag calibration architecture cleanup | IMU | 1h |
| **MEDIUM** | Ellipsoid fitting for soft-iron | IMU/Calibration | 3h |
| **MEDIUM** | Madgwick gain tuning test | IMU/Localization | 30 min test |
| **MEDIUM** | PID tuning tool (webgui page) | PID/UX | 4-6h |
| **LOW** | Mag flash persistence | Firmware | 3h |
| **LOW** | Per-axis IMU covariance | ROS2 | 30 min |
| **LOW** | PID output normalization | Firmware | 2h |

---

## Test Commands

```bash
# IMU noise measurement (robot stationary, flat, 30 seconds)
ros2 run orbibot_localization measure_imu_noise

# Verify EKF frequency
ros2 topic hz /odometry/filtered  # Should be ~25Hz

# Check accel bias (X,Y should be near 0 after firmware update)
ros2 topic echo /imu/data_raw --field linear_acceleration --once

# Madgwick config override test
ros2 launch orbibot_localization localization.launch.py \
  madgwick_config:=/path/to/custom_madgwick.yaml

# PID step response test (enable motors first)
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: true}'
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.3}, angular: {z: 0.0}"
# Watch /odom velocity response — should reach 0.3 m/s within 1-2 seconds
```
