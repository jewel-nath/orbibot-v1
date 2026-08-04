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

- Every covariance and tuning figure predates the 2026-08-03 accel fix and
  should be re-measured — roadmap Phase 4. **In progress 2026-08-04:**
  `measure_imu_noise` now reports gyro bias and measured yaw drift alongside
  the variances, and a 10-minute stationary run is what Phase 4.1 and roadmap
  1.3 are waiting on
- `zeta: 0.0` has never been tested against a measured drift figure. Raising it
  is only justifiable once that figure exists

Closed 2026-08-04: **CC-4** — the README's magnetometer claim was fixed back in
`bf8d74f`; the backlog entry had simply never been closed.

## Related

[[packages-moc]] · [[orbibot_hardware]] · [[orbibot_slam]] ·
[[system-overview]] · [[localization-moc]]
