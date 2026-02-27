# orbibot_localization — Audit Findings

**Date:** 2026-02-23
**Audited:** `config/ekf_params.yaml`, `launch/localization.launch.py`, `README.md`
**References compared:** `References/Yahboom_RosMasterX3_Robot/robot_localization_ref/ekf_x1_x3.yaml`, `References/LGDXRobot2/lgdxrobot2-ros2/lgdxrobot2_bringup/param/ekf.yaml`

---

## Progress Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

---

## Architecture Assessment

**Verdict: Architecture is sound. No structural changes required.**

The localization stack uses the correct pipeline:

```
/imu/data_raw + /imu/mag → imu_filter_madgwick → /imu/data_filtered → EKF
/odom (wheel odometry) ─────────────────────────────────────────────→ EKF
EKF → /odometry/filtered + odom→base_footprint TF
```

Key design decisions confirmed as correct:
- **Velocity-only odom fusion** (`odom0_config` position=false, velocity=true): prevents pose drift accumulation from direct encoder position integration — better than Yahboom reference which fuses raw x/y position
- **Absolute yaw from Madgwick + yaw rate**: matches both LGDXRobot2 and Yahboom reference patterns; Madgwick running on raw data gives tunable ROS-side filter vs firmware complementary filter (which publishes on `/imu/data`)
- **`imu0_relative: true`**: correct — makes yaw relative to first measurement so EKF always starts at yaw=0 regardless of robot heading at startup
- **`two_d_mode: true`**: correct for planar mecanum robot
- **`base_link_frame: base_footprint`**: correct per project convention

---

## Issues Found

### Bugs

| ID | Severity | File | Description |
|----|----------|------|-------------|
| BUG-1 | Medium | `ekf_params.yaml` | `sensor_timeout: 0.5` is too lenient for 50Hz sensor — EKF stalls up to 25 missed samples before switching to predict-only; should be `0.1` |
| BUG-2 | Low | `README.md` | IMU topic listed as `/imu/data` — actual config uses `/imu/data_filtered` (Madgwick output) |
| BUG-3 | Low | `README.md` | Describes "differential mode" for IMU — config has `imu0_differential: false` (absolute mode) |

### Improvements

| ID | File | Description |
|----|------|-------------|
| Q1 | `ekf_params.yaml` | Missing `reset_on_time_jump: true` — important for rosbag-based debugging/testing |
| Q2 | `ekf_params.yaml` | `imu0_pose_rejection_threshold: 2.5` too aggressive — Mahalanobis threshold of 2.5 will reject valid Madgwick yaw corrections under mecanum vibration; Yahboom reference uses 20.0; raise to `15.0` |

### Documentation

| ID | Description |
|----|-------------|
| C1 | README missing: full topic/TF table, tuning guide, frame convention explanation, dependency install commands |

---

## Reference Comparison Notes

| Parameter | OrbiBot | Yahboom X3 | LGDXRobot2 | Assessment |
|-----------|---------|-----------|-----------|------------|
| `frequency` | 25 Hz | 30 Hz | 50 Hz | OK — RPi 5 can handle 25Hz |
| `sensor_timeout` | 0.5 s | 0.1 s | (default) | **Fix** — too lenient |
| `odom0_config` (positions) | false | true | false | OrbiBot correct — velocity-only is better |
| `imu0_differential` | false | false | false | OK — all use absolute |
| `imu0_relative` | true | true | (not set) | OK |
| `imu0_pose_rejection_threshold` | 2.5 | 20.0 | (not set) | **Fix** — too strict |
| `reset_on_time_jump` | missing | true | (not set) | **Add** |
| `process_noise_covariance` | OrbiBot yaw=0.03 | yaw=0.06 | — | OK — intentional lower yaw noise with Madgwick |
| `initial_estimate_covariance` | 1e-6 | 1e-9 | — | Negligible difference in practice |

---

## Fix Status

- [x] BUG-1 — `sensor_timeout: 0.5` → `0.1`
- [x] Q2 — `imu0_pose_rejection_threshold: 2.5` → `15.0`
- [x] Q1 — Add `reset_on_time_jump: true`
- [x] BUG-2 + BUG-3 + C1 — Rewrite README
