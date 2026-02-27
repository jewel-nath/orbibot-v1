# orbibot_msgs

Custom ROS 2 message and service definitions for OrbiBot.

## Messages

| Message | Description | Status |
|---------|-------------|--------|
| `SystemStatus` | Battery voltage, motor enable state, hardware health | Active — used by hardware_node, system_monitor |
| `SafetyStatus` | Emergency stop, timeouts, faults, velocity limit flag | Active — used by hardware_node, control_manager |
| `WheelSpeeds` | Individual mecanum wheel speeds (m/s) | Reserved for future use |
| `MotorFeedback` | Encoder counts, positions, velocities, motor status | Reserved for future use |

## Services

| Service | Description | Status |
|---------|-------------|--------|
| `SetMotorEnable` | Enable or disable motors | Active — hardware_node server |
| `ResetOdometry` | Reset odometry to zero or a given pose | Active — control_manager server |
| `CalibrateIMU` | Run IMU calibration for a specified duration | Placeholder |

## Dependencies

- `std_msgs` — Header timestamps
- `geometry_msgs` — Pose type for odometry reset
