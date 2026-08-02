---
title: "orbibot_localization"
type: package
tags:
  - package
  - localization
---

# orbibot_localization

Two-stage fusion: Madgwick for orientation, then an EKF that combines it with
wheel odometry and publishes `odom → base_footprint`.

> **The API reference is `src/orbibot_localization/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

```
/imu/data_raw ─► imu_filter_madgwick ─► /imu/data_filtered ─┐
                 use_mag: false                             ├─► EKF ─► /odometry/filtered
/odom ──────────────────────────────────────────────────────┘        TF: odom → base_footprint
```

```bash
ros2 launch orbibot_localization localization.launch.py
```

Config: `madgwick_params.yaml`, `ekf_params.yaml`.

## The thing to understand

**There is no absolute heading reference.** The magnetometer was removed on
2026-04-28 — indoors, steel, motors and battery currents distort the field
enough to make heading worse, not better.

So Madgwick runs 6-DoF, the EKF takes IMU yaw in *relative* mode
(`imu0_relative: true` — the first reading becomes zero), and yaw drift is
corrected further up by slam_toolbox or AMCL through `map → odom`.

`zeta` in `madgwick_params.yaml` is now the parameter that matters: with no
magnetometer it is what fights gyro bias.

## Open

- **`README.md` still says Madgwick "fuses raw IMU + magnetometer"** — wrong
  since April, [[backlog-moc]] CC-4
- Every covariance and tuning figure predates the 2026-08-03 accel fix and
  should be re-measured — roadmap Phase 4

## Related

[[packages-moc]] · [[orbibot_hardware]] · [[orbibot_slam]] ·
[[system-overview]] · [[localization-moc]]
