---
title: "orbibot_hardware"
type: package
tags:
  - package
  - hardware
---

# orbibot_hardware

The bridge. Turns the STM32's binary serial stream into ROS 2 topics, and
`/cmd_vel` into motion.

> **The API reference is `src/orbibot_hardware/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

| Publishes | |
|---|---|
| `/odom` | Raw wheel odometry, velocity-only |
| `/orbibot/encoders` | `Int32MultiArray` [FL, BL, FR, BR], 50 Hz |
| `/imu/data_raw` | Gyro + accel. 12-byte packet — **no magnetometer** |
| `/imu/data` | The firmware's own attitude estimate |
| `/joint_states` | Wheel positions for TF |
| `/orbibot/system_status`, `/orbibot/safety_status`, `/diagnostics` | Battery, motor enable, faults |

Subscribes `/cmd_vel`. Serves `SetMotorEnable`, `ResetOdometry`,
`ResetEncoders`, `CalibrateIMU`, `GetFirmwareVersion`.

```bash
ros2 launch orbibot_hardware hardware.launch.py
```

## Look first

`orbibot_hardware/rosmaster_driver.py` is the protocol half —
`hardware_node.py` is the ROS half. When firmware and driver disagree about a
packet, this is where it goes silent: each branch length-checks and returns.
That is how the raw IMU path stayed dead for months.

## Open

- `hardware-issue.md` — 6 entries
- It subscribes `/cmd_vel` directly, which is why four publishers can fight —
  [[command-pipeline]]

## Related

[[packages-moc]] · [[orbibot_rosmaster_firmware]] · [[orbibot_localization]] ·
[[command-pipeline]] · [[hardware-moc]]
