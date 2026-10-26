# System Overview

Two computers. The STM32 closes the fast loops; the Pi does everything that
needs a map, a model, or a network.

```
                     ┌─────────────────────────────────────────┐
   RPLidar A1 ──USB──┤                                         │
   RealSense  ──USB──┤        Raspberry Pi 5  (ROS 2 Jazzy)    │
                     │                                         │
                     └───────────────────┬─────────────────────┘
                                         │ USB serial, 115200
                     ┌───────────────────┴─────────────────────┐
                     │   ROSMaster V3.0 — STM32F103RCT6        │
                     │   PID @ 100 Hz · encoders · ICM-20948   │
                     └───┬───────┬───────┬───────┬─────────────┘
                        M1      M2      M3      M4
                        FL      BL      FR      BR
```

**The split matters.** Anything with a deadline — PID, encoder counting, the
2 s command timeout — lives on the STM32, where nothing can preempt it. The Pi
never has to be real-time, which is why a busy dashboard cannot make the wheels
stutter.

## Data flowing up

| From | Topic | Rate | Note |
|---|---|---|---|
| firmware | `/odom` | on change + 0.5 s heartbeat | Raw wheel odometry, velocity-only |
| firmware | `/orbibot/encoders` | 50 Hz | `Int32MultiArray` [FL, BL, FR, BR] |
| firmware | `/imu/data_raw` | 50 Hz | 12-byte packet: gyro + accel. **No magnetometer** |
| firmware | `/imu/data` | 50 Hz | Firmware's own attitude estimate |
| firmware | `/joint_states` | 50 Hz | Wheel positions for TF |
| firmware | `/orbibot/system_status`, `/orbibot/safety_status`, `/diagnostics` | — | Battery, motor enable, faults |
| RPLidar A1 | `/scan` | 5.5 Hz nominal | 360°, used to 8 m |

## The estimation chain

```
/imu/data_raw ──► imu_filter_madgwick ──► /imu/data_filtered ──┐
                  (use_mag: false)                             │
                                                               ├─► EKF
/odom ─────────────────────────────────────────────────────────┘   │
                                                                   ▼
                                              /odometry/filtered
                                              TF: odom → base_footprint
```

**Heading has no absolute reference.** The magnetometer was removed on
2026-04-28 — indoors, steel, motors and battery currents distort the field
enough to make it worse than useless. Madgwick therefore runs 6-DoF, the EKF
takes IMU yaw in *relative* mode (`imu0_relative: true`, first reading becomes
zero), and yaw drift is corrected further up by slam_toolbox or AMCL through
`map → odom`.

The consequence for testing: a test of the base on its own cannot prove the
heading is right. It can only bound how fast the yaw drifts. Absolute heading
is the map's job.

## TF chain

```
map → odom → base_footprint → base_link → sensor_links
```

- `map → odom` — exactly one publisher, ever: slam_toolbox **or** AMCL
- `odom → base_footprint` — the EKF
- `base_footprint → base_link` and below — URDF, `orbibot_description`

**The base frame is `base_footprint`, never `base_link`.** Consumers use
`/odometry/filtered`, not `/odom`.

## Commands flowing down

Covered in [Command Pipeline](command-pipeline.md) — including the fact that four things publish
`/cmd_vel` today and nothing arbitrates between them.

## Launch layering

Each package launches only its own nodes. Composition lives in
[orbibot_bringup](../../src/orbibot_bringup/README.md):

```bash
ros2 launch orbibot_bringup robot.launch.py        # description + hardware + EKF + LiDAR
ros2 launch orbibot_bringup mapping.launch.py      # slam_toolbox + Nav2 (start the base first)
ros2 launch orbibot_bringup exploration.launch.py  # slam_toolbox + Nav2 + frontier explorer
ros2 launch orbibot_webgui  webgui.launch.py       # rosbridge :9090, WebRTC :8081
```

## Related

[Docs home](../README.md) · [Command Pipeline](command-pipeline.md) · [Dashboard Design](dashboard-design.md) ·
[Packages](../packages.md) · [OrbiBot Hardware Documentation](../hardware/rosmaster-board.md) · [OrbiBot ROSMaster Firmware - Architecture Design](../../src/orbibot_rosmaster_firmware/firmware-architecture.md)
