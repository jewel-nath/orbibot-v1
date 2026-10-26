# orbibot_msgs

OrbiBot's own message and service definitions. The set is small on purpose:
standard ROS 2 types are used wherever they fit.

**Status:** used on the robot, by `orbibot_hardware` and the agent.

## Messages

| Message | What it carries | Used by |
|---|---|---|
| `SystemStatus` | Battery voltage, motor enable state, hardware health | `hardware_node` and `system_monitor` publish it; the agent reads it |
| `SafetyStatus` | Emergency stop, timeouts, faults, the velocity-limit flag | `hardware_node` publishes it; the agent reads it |
| `WheelSpeeds` | The four mecanum wheel speeds (m/s) | Defined, not used yet |
| `MotorFeedback` | Encoder counts, positions, velocities, motor status | Defined, not used yet |

## Services

All five are served by `hardware_node` in
[orbibot_hardware](../orbibot_hardware/README.md).

| Service | What it does |
|---|---|
| `SetMotorEnable` | Turns the motors on or off |
| `ResetOdometry` | Resets the odometry to zero or to a given pose |
| `ResetEncoders` | Sets the encoder counts back to zero |
| `CalibrateIMU` | Runs an IMU calibration for a given time |
| `GetFirmwareVersion` | Asks the STM32 for its firmware version |

`SetMagCalibration` was removed on 2026-04-28 with the rest of the
magnetometer code.

## Dependencies

`std_msgs` (header timestamps) and `geometry_msgs` (the pose for
`ResetOdometry`).
