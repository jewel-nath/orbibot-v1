# orbibot_localization

EKF sensor fusion for OrbiBot using `robot_localization`. Fuses wheel odometry with IMU data (via Madgwick filter) to produce drift-reduced odometry for navigation.

## Overview

This package implements a two-stage sensor fusion pipeline:
1. **Madgwick Filter** (50 Hz): gyro + accel → orientation. **6-DoF, `use_mag: false`**
2. **EKF** (25 Hz): wheel velocities + Madgwick orientation → smooth odometry

**Yaw is not absolute and not drift-free.** The magnetometer was removed on
2026-04-28 — indoors, steel and motor currents made heading worse than dead
reckoning. The EKF takes IMU yaw in *relative* mode (`imu0_relative: true`),
and absolute heading is the map's job: slam_toolbox or AMCL correct it through
`map → odom`.

This architecture provides better yaw accuracy than EKF alone while maintaining computational efficiency.

---

## Architecture

```
SENSOR FUSION PIPELINE

  /imu/data_raw            50 Hz   gyro + accel. No magnetometer.
        │
        ▼
  imu_filter_madgwick      50 Hz   use_mag: false  → 6-DoF
        │                          gain 0.1 · zeta 0.0 · stddev 0.05
        ▼
  /imu/data_filtered       50 Hz   orientation quaternion
        │                          yaw is RELATIVE and drifts
        │
        │   /odom          20 Hz   wheel velocities, from orbibot_hardware
        │        │
        └────────┴──► EKF (robot_localization)      25 Hz
                        │   fuses vx, vy from /odom
                        │   fuses yaw, vyaw from the IMU
                        │   imu0_relative: true  — first reading becomes zero
                        ▼
                  /odometry/filtered
                  + TF  odom → base_footprint

Absolute heading comes from neither of these. slam_toolbox or AMCL
corrects yaw further up, through map → odom.
```

---

## Why This Design?

### Velocity-Only Odometry Fusion
The EKF is configured with `odom0_config` positions=false. This prevents wheel encoder position drift from accumulating in the filter state. Only velocities are fused, with IMU providing absolute yaw correction.

### Madgwick + EKF (Two-Stage)
- **Madgwick** runs at 50 Hz on gyro + accel → orientation (6-DoF, no magnetometer)
- **EKF** fuses this with wheel odometry at 25 Hz → smooth, computationally efficient

This provides better yaw accuracy than EKF alone while keeping CPU usage low.

---

## Quick Start

```bash
# Launch localization stack
ros2 launch orbibot_localization localization.launch.py

# With debug logging
ros2 launch orbibot_localization localization.launch.py log_level:=debug
```

**Prerequisites**: `robot.launch.py` must be running (publishing `/odom` and `/imu/*`)

---

## Launch Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `ekf_config` | `config/ekf_params.yaml` | Path to EKF configuration file |
| `log_level` | `info` | Logging level: `debug`, `info`, `warn`, `error` |

---

## Topics

### Subscribed

| Topic | Type | Source | Rate | Description |
|-------|------|--------|------|-------------|
| `/imu/data_raw` | `sensor_msgs/Imu` | `orbibot_hardware` | 50 Hz | Raw accelerometer + gyroscope |
| `/odom` | `nav_msgs/Odometry` | `orbibot_hardware` | 20 Hz | Wheel odometry (velocities) |

### Published

| Topic | Type | Rate | Description |
|-------|------|------|-------------|
| `/imu/data_filtered` | `sensor_msgs/Imu` | 50 Hz | Madgwick-filtered IMU with orientation quaternion |
| `/odometry/filtered` | `nav_msgs/Odometry` | **24.0–24.5 Hz measured** (25 configured) | EKF-fused odometry for Nav2/SLAM. The ~2.5 Hz of HW-BUG-1 was a Pi-era symptom and does not occur on the Beelink |

### TF Published

| Transform | Publisher | Description |
|-----------|-----------|-------------|
| `odom → base_footprint` | EKF node | Robot pose in odometry frame |

---

## EKF Configuration

### What Is Fused (`config/ekf_params.yaml`)

#### odom0 (`/odom`) — Wheel Odometry

| Variable | Fused | Reason |
|----------|-------|--------|
| x, y, z position | **No** | Prevents encoder drift accumulation |
| roll, pitch, yaw | **No** | IMU provides better heading |
| vx, vy (linear) | **Yes** | Mecanum wheel velocities |
| vz | No | Planar robot |
| vroll, vpitch | No | Planar robot (two_d_mode) |
| vyaw (angular) | **Yes** | Yaw rate from wheel kinematics |

#### imu0 (`/imu/data_filtered`) — Madgwick Output

| Variable | Fused | Reason |
|----------|-------|--------|
| roll, pitch | No | Planar robot (two_d_mode) |
| yaw | **Yes** | Madgwick yaw, **relative** (`imu0_relative: true`) — not absolute |
| vx, vy, vz | No | Not provided by IMU |
| vroll, vpitch, vyaw | **Yes** | Gyroscope rates |
| ax, ay, az | **No** | Disabled — mecanum vibration causes noise |

### Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `frequency` | 25.0 Hz | EKF output rate. Set for a Raspberry Pi 5 that has since been replaced — re-derive, see roadmap 4.5 |
| `sensor_timeout` | 0.15 s | Max wait before prediction-only |
| `two_d_mode` | true | Planar robot — ignore z/roll/pitch |
| `imu0_differential` | false | Use absolute yaw (not differentiated) |
| `imu0_relative` | true | Yaw starts at 0 regardless of initial heading |
| `reset_on_time_jump` | true | Reset filter on rosbag time jumps |

### Process Noise Covariance

| State | Value | Notes |
|-------|-------|-------|
| x, y | 0.05 | Position uncertainty growth |
| yaw | 0.03 | Lower than reference — IMU provides good heading |
| vx, vy | 0.025 | Velocity uncertainty |
| vyaw | 0.01 | Low — Madgwick constrains yaw rate well |

### Rejection Thresholds (Mahalanobis distance)

| Parameter | Value | Effect |
|-----------|-------|--------|
| `odom0_twist_rejection_threshold` | 1.0 | Rejects odometry velocity spikes |
| `imu0_pose_rejection_threshold` | 15.0 | Permissive — avoids rejecting valid yaw under vibration |
| `imu0_twist_rejection_threshold` | 2.5 | Moderate — filters gyro spikes |

---

## Frame Conventions

```
map (world frame, from SLAM)
└── odom (odometry origin, drifts slowly)
    └── base_footprint (robot footprint on ground)
        └── base_link (robot center)
            └── sensors... (lidar_link, imu_link, camera_link)
```

- **EKF publishes**: `odom → base_footprint`
- **robot_state_publisher provides**: `base_footprint → base_link → sensors`
- **SLAM publishes**: `map → odom` (corrects drift)

---

## Tuning Guide

### IMU Noise Measurement

```bash
# Robot stationary and level, 30 s
ros2 run orbibot_localization measure_imu_noise
```

Writes measured accel/gyro variances for the EKF covariance diagonals. The
values currently in `hardware_params.yaml` were taken through a faulty
accelerometer path and are **suspect** — re-measure before trusting them. See
`docs/moc/backlog-moc.md` CC-3.

> There is no magnetometer calibration. `calibrate_magnetometer` was deleted
> along with magnetometer support on 2026-04-28.

### Madgwick Filter (`localization.launch.py`)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `gain` | 0.1 | Higher = faster convergence, more noise sensitivity |
| `zeta` | 0.0 | Gyro bias drift correction. Disabled — with `use_mag: false` there is no absolute reference to drive it |
| `use_mag` | false | Magnetometer removed 2026-04-28. Do not re-enable |
| `frequency` | 50.0 | Must match IMU publish rate |
| `orientation_stddev` | 0.05 | ~3° — how much the EKF trusts Madgwick yaw |

### When to Tune EKF

| Symptom | Adjustment |
|---------|------------|
| Yaw drifts slowly | Expected without a magnetometer. Bound it (roadmap 1.3); correction is SLAM/AMCL's job |
| Yaw jumps/jitters | Decrease Madgwick `gain`; increase `imu0_pose_rejection_threshold` |
| Position drifts | Normal for wheel odometry — ensure loop closure in SLAM |
| Position jumps | Increase `odom0_twist_rejection_threshold` |
| Slow response | Decrease `process_noise_covariance` for vx/vy |
| Noisy estimate | Increase `process_noise_covariance` for vx/vy |

---

## Debugging

### Verify Data Flow
```bash
# Check all topics are publishing
ros2 topic hz /imu/data_raw           # ~50Hz
ros2 topic hz /imu/data_filtered      # ~50Hz
ros2 topic hz /odom                   # ~20Hz
ros2 topic hz /odometry/filtered      # ~24Hz measured 2026-08-03

# Inspect EKF output
ros2 topic echo /odometry/filtered --once
# Look for: pose (x,y,yaw), twist (vx,vy,vyaw), covariance
```

### Check TF Tree
```bash
ros2 run tf2_tools view_frames
# Verify: odom → base_footprint exists
```

### EKF Diagnostics
```bash
# Check EKF health
ros2 topic echo /diagnostics

# Look for:
# - "robot_localization_ekf: IMU message contains NaN" → Check IMU data
# - "robot_localization_ekf: Odometry message contains NaN" → Check /odom
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No `/odometry/filtered` | Missing inputs | Check `/odom` and `/imu/data_filtered` publishing |
| Yaw drifts continuously | Expected — gyro-only heading | Only `map → odom` fixes this. Check slam_toolbox/AMCL is running |
| Position jumps | Wheel slip | Increase `odom0_twist_rejection_threshold` |
| TF extrapolation errors | Timing issues | Check `transform_timeout` and `sensor_timeout` |
| High covariance | Poor sensor agreement | Check IMU vs odometry consistency |

---

## Dependencies

```bash
sudo apt install ros-jazzy-robot-localization
sudo apt install ros-jazzy-imu-filter-madgwick
```

---

## References

- **robot_localization**: https://docs.ros.org/en/jazzy/p/robot_localization/
- **Madgwick Filter**: https://x-io.co.uk/open-source-imu-and-ahrs-algorithms/
- **IMU Fusion Theory**: https://doi.org/10.1109/TIST.2011.2179576

---

**Last Updated**: 2026-03-01  
**Maintainer**: Jewel Nath
