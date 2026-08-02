---
title: "orbibot_msgs"
type: package
tags:
  - package
  - msgs
---

# orbibot_msgs

Custom message and service definitions. Small on purpose — standard ROS 2
types are used wherever they fit.

> **The API reference is `src/orbibot_msgs/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

| Messages | Services |
|---|---|
| `MotorFeedback` | `SetMotorEnable` |
| `SafetyStatus` | `ResetOdometry` |
| `SystemStatus` | `ResetEncoders` |
| `WheelSpeeds` | `CalibrateIMU` |
| | `GetFirmwareVersion` |

`SetMagCalibration.srv` was deleted on 2026-04-28 with the rest of the
magnetometer pipeline. Do not recreate it.

## Related

[[packages-moc]] · [[orbibot_hardware]]
