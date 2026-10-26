# orbibot_localization

OrbiBot's state estimation, in two stages: a Madgwick filter turns the raw
IMU into an orientation, and an EKF combines that with wheel odometry. The
EKF publishes `/odometry/filtered` and the `odom → base_footprint` transform.

**Status:** runs on the robot inside `robot.launch.py`. Tuned in March 2026,
before the IMU fixes, so it needs tuning again: every
covariance and drift figure recorded before 2026-08-03 was measured while the
IMU had two faults (see [status](../../docs/status.md)), so they need
measuring again.

## How it fits together

```
/imu/data_raw ─► imu_filter_madgwick ─► /imu/data_filtered ─┐
 (gyro + accel)   use_mag: false                            ├─► EKF ─► /odometry/filtered
/odom ──────────────────────────────────────────────────────┘          TF: odom → base_footprint
 (wheel odometry from orbibot_hardware)
```

**There is no absolute heading.** The IMU's magnetometer was removed on
2026-04-28: indoors, the steel frame, the motors and the battery currents
bent the magnetic field enough to make the heading worse, not better. So:

- Madgwick runs on gyro and accelerometer only (`use_mag: false`);
- the EKF takes the IMU's yaw in relative mode (`imu0_relative: true`): the
  first reading becomes zero;
- yaw drift is corrected further up, by slam_toolbox or AMCL through
  `map → odom`.

## Launch

```bash
ros2 launch orbibot_localization localization.launch.py
ros2 launch orbibot_localization localization.launch.py log_level:=debug
```

| Argument | Default |
|---|---|
| `ekf_config` | `config/ekf_params.yaml` |
| `madgwick_config` | `config/madgwick_params.yaml` |
| `log_level` | `info` |

`robot.launch.py` starts this 3 s after the hardware node.

## Topics

| Topic | Type | Direction | From or to |
|---|---|---|---|
| `/imu/data_raw` | `sensor_msgs/Imu` | in | `orbibot_hardware`, about 50 Hz |
| `/odom` | `nav_msgs/Odometry` | in | `orbibot_hardware` |
| `/imu/data_filtered` | `sensor_msgs/Imu` | out (Madgwick) | the EKF |
| `/odometry/filtered` | `nav_msgs/Odometry` | out (EKF) | Nav2 and anything else that needs odometry |
| TF `odom → base_footprint` | | out (EKF) | |

`/odom` is raw wheel odometry. Consumers should use `/odometry/filtered`.

## Configuration

### Madgwick (`config/madgwick_params.yaml`)

| Parameter | Value | Why |
|---|---|---|
| `use_mag` | `false` | No magnetometer |
| `gain` | `0.1` | A common value for robots; higher converges faster but follows vibration more |
| `zeta` | `0.0` | Gyro-bias correction, off: without a magnetometer it has no reference |
| `orientation_stddev` | `0.05` | About 3°, the uncertainty reported to the EKF |
| `frequency` | `50.0` | Matches the IMU rate |
| `publish_tf` | `false` | Only the EKF publishes `odom → base_footprint` |

### EKF (`config/ekf_params.yaml`)

| Setting | Value |
|---|---|
| Rate | 25 Hz, `two_d_mode: true` |
| Frames | `world_frame: odom`, `base_link_frame: base_footprint` |
| `odom0` (`/odom`) | Fuses vx, vy and the yaw rate only. Positions are not fused, so wheel slip doesn't pile up in the filter |
| `imu0` (`/imu/data_filtered`) | Fuses yaw (relative) and the yaw rate. Accelerations are off: mecanum rollers make them noisy |
| Rejection thresholds | Raised for the vibration of a mecanum base: IMU pose 15, twist 2.5 |

## Measuring the IMU's noise

`measure_imu_noise` records `/imu/data_raw` while the robot stands still and
prints per-axis variances for `hardware_params.yaml`:

```bash
ros2 run orbibot_localization measure_imu_noise   # don't touch the robot for 30 s
```

The values in `orbibot_hardware/config/hardware_params.yaml` came from this
tool on 2026-03-24 (212 samples).

## Checking it

```bash
ros2 topic hz /imu/data_raw          # about 50 Hz
ros2 topic hz /imu/data_filtered     # about 50 Hz
ros2 topic hz /odometry/filtered     # about 25 Hz
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 topic echo /diagnostics         # the EKF's own diagnostics
```

| Symptom | Where to look |
|---|---|
| No `/odometry/filtered` | Is `/odom` arriving? The EKF waits for its inputs |
| Yaw slowly drifts with no SLAM running | Expected: there is no absolute heading |
| The robot jumps in RViz | Two nodes publishing `odom → base_footprint`; only the EKF should |
| `IMU message contains NaN` | Check `/imu/data_raw` from the hardware node |
