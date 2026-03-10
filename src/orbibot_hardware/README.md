# orbibot_hardware

ROS 2 hardware interface for OrbiBot. Bridges the Yahboom ROSMaster V3.0 expansion board (STM32) to the ROS 2 ecosystem via serial protocol.

---

## Nodes

### hardware_node (`orbibot_hardware_node`)

Publishes sensor data and accepts velocity/PID commands.

#### Subscriptions

| Topic | Type | QoS | Description |
|-------|------|-----|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Reliable | Velocity commands forwarded to firmware |
| `/orbibot/pid_params` | `std_msgs/Float32MultiArray` | Default | Motor PID gains `[kp, ki, kd]` — all motors |
| `/orbibot/yaw_pid_params` | `std_msgs/Float32MultiArray` | Default | Yaw PID gains `[kp, ki, kd]` |
| `/orbibot/pid_multilevel` | `std_msgs/Float32MultiArray` | Default | Multi-level PID: `[t0,t1,t2, kp0,ki0,kd0, kp1,ki1,kd1, kp2,ki2,kd2]` |
| `/orbibot/pid_save` | `std_msgs/Float32MultiArray` | Default | Save PID to flash — same 12-value format as `pid_multilevel` |
| `/orbibot/beep` | `std_msgs/UInt16` | Default | Buzzer: `0`=off, `1`=continuous, `≥10`=on for N ms then auto-off |

#### Publications

| Topic | Type | QoS | Rate | Description |
|-------|------|-----|------|-------------|
| `/odom` | `nav_msgs/Odometry` | Reliable, TRANSIENT_LOCAL (depth 5) | ~20Hz (heartbeat when idle) | Firmware wheel odometry; deduplicated; re-published at `odometry.heartbeat_interval` when unchanged so late joiners (e.g. web GUI) get data |
| `/imu/data` | `sensor_msgs/Imu` | Best Effort (depth 5) | 50Hz | Filtered attitude (orientation) + accel + gyro |
| `/imu/data_raw` | `sensor_msgs/Imu` | Best Effort (depth 5) | 50Hz | Raw accel + gyro, no orientation (for imu_filter_madgwick) |
| `/imu/mag` | `sensor_msgs/MagneticField` | Best Effort (depth 5) | 50Hz | Magnetometer in Tesla (skipped if all-zero) |
| `/orbibot/encoders` | `std_msgs/Int32MultiArray` | Best Effort (depth 5) | 50Hz | Raw encoder counts `[FL, BL, FR, BR]` in ticks |
| `/joint_states` | `sensor_msgs/JointState` | Reliable (depth 10) | 50Hz | Wheel positions (rad) for RViz visualization |
| `/orbibot/system_status` | `orbibot_msgs/SystemStatus` | Reliable (depth 10) | 10Hz | Battery voltage, motor state, hardware health |
| `/orbibot/safety_status` | `orbibot_msgs/SafetyStatus` | Reliable (depth 10) | 10Hz | Emergency stop, timeouts, faults |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | Reliable (depth 10) | 10Hz | Standard ROS diagnostics |

#### Services

| Service | Type | Description |
|---------|------|-------------|
| `/orbibot/set_motor_enable` | `orbibot_msgs/SetMotorEnable` | Enable/disable motors |
| `/orbibot/calibrate_imu` | `orbibot_msgs/CalibrateIMU` | IMU calibration (ICM-20948 auto-calibrates on startup — returns not supported) |
| `/orbibot/reset_odometry` | `orbibot_msgs/ResetOdometry` | Reset firmware position + covariance accumulators to zero |

---

### system_monitor (`system_monitor`)

Enriches hardware status with host resource metrics.

#### Subscriptions
| Topic | Type | Description |
|-------|------|-------------|
| `/orbibot/system_status` | `orbibot_msgs/SystemStatus` | Hardware status from hardware_node |

#### Publications
| Topic | Type | Rate | Description |
|-------|------|------|-------------|
| `/orbibot/system_status_enriched` | `orbibot_msgs/SystemStatus` | 1Hz | Battery + CPU%, RAM%, CPU temp°C, disk% |

---

## Launch

```bash
ros2 launch orbibot_hardware hardware.launch.py
ros2 launch orbibot_hardware hardware.launch.py serial_port:=/dev/ttyUSB0
ros2 launch orbibot_hardware hardware.launch.py motors_enabled:=false
```

| Argument | Default | Description |
|----------|---------|-------------|
| `serial_port` | `/dev/motordriver` | Serial port for motor driver board |
| `motors_enabled` | `true` | Auto-enable motors 6s after startup (single call) |

Both nodes launch with `respawn=True` for automatic recovery.

---

## Configuration

See [config/hardware_params.yaml](config/hardware_params.yaml) for all parameters:

| Section | Parameter | Default | Description |
|---------|-----------|---------|-------------|
| `hardware` | `serial_port` | `/dev/motordriver` | Serial device path |
| `hardware` | `data_timeout` | `2.0` s | No firmware data for this long → hardware_connected=false |
| `robot` | `wheel_radius` | `0.05` m | Wheel radius (50 mm) |
| `robot` | `encoder_edges_per_rev` | `1320` | Encoder edges per wheel revolution |
| `control` | `cmd_timeout` | `2.0` s | Stop if no `/cmd_vel` received in this window |
| `control` | `max_velocity` | `1.0` m/s | Linear velocity clamp |
| `control` | `max_angular_velocity` | `2.0` rad/s | Angular velocity clamp |
| `rates` | `sensor_rate` | `50.0` Hz | IMU, encoder, joint state publish rate |
| `rates` | `status_rate` | `10.0` Hz | System/safety status publish rate |
| `safety` | `battery_low_threshold` | `11.0` V | Low battery warning level |
| `safety` | `battery_critical_voltage` | `10.5` V | Emergency stop threshold |
| `imu` | `linear_acceleration_covariance` | `0.01` | IMU accel covariance (diagonal) |
| `imu` | `angular_velocity_covariance` | `0.0025` | IMU gyro covariance (diagonal) |
| `imu` | `orientation_covariance` | `0.0025` | IMU orientation covariance (diagonal) |
| `odometry` | `pose_base` | `0.001` | Base position variance (m²) |
| `odometry` | `pose_drift` | `0.02` | Position variance drift per meter traveled |
| `odometry` | `yaw_base` | `0.01` | Base yaw variance (rad²) |
| `odometry` | `yaw_drift` | `0.005` | Yaw variance drift per radian rotated |
| `odometry` | `velocity_base` | `0.01` | Base velocity variance ((m/s)²) |
| `odometry` | `velocity_scale` | `0.1` | Velocity variance scale with speed |
| `odometry` | `covariance_decay` | `0.99` | Exponential decay for accumulated drift (0–1) |
| `odometry` | `heartbeat_interval` | `0.5` s | Re-publish unchanged odom so late-joining subscribers get data; `0` = disable |

---

## PID Tuning via Topics

```bash
# Set motor PID gains (temporary, single-level)
ros2 topic pub --once /orbibot/pid_params std_msgs/msg/Float32MultiArray \
  "data: [0.8, 0.06, 0.5]"

# Set multi-level PID (thresholds mm/s, gains float [0,10])
# Format: [t0, t1, t2, kp0, ki0, kd0, kp1, ki1, kd1, kp2, ki2, kd2]
ros2 topic pub --once /orbibot/pid_multilevel std_msgs/msg/Float32MultiArray \
  "data: [100.0, 300.0, 600.0, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5]"

# Save current multi-level PID to flash
ros2 topic pub --once /orbibot/pid_save std_msgs/msg/Float32MultiArray \
  "data: [100.0, 300.0, 600.0, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5]"
```

## Buzzer Examples

```bash
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 200"  # Beep 200ms
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 1"    # Continuous
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 0"    # Off
```

---

## Debug Commands

```bash
# Launch hardware node
ros2 launch orbibot_hardware hardware.launch.py

# Check topics are publishing
ros2 topic hz /odom                          # ~20Hz when firmware connected
ros2 topic hz /imu/data                      # ~50Hz
ros2 topic hz /orbibot/encoders              # ~50Hz

# Inspect data
ros2 topic echo /odom                        # Position + velocity + covariance
ros2 topic echo /imu/data                    # Quaternion + accel + gyro
ros2 topic echo /orbibot/system_status       # Battery, motor enable state

# Enable/disable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: true}'
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: false}'

# Reset odometry
ros2 service call /orbibot/reset_odometry orbibot_msgs/srv/ResetOdometry '{}'

# Manual velocity test (motors must be enabled first)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {z: 0.0}"

# Check serial port
ls -la /dev/motordriver
screen /dev/motordriver 115200              # Direct serial monitor (Ctrl+A K to quit)
```

---

## Implementation Notes

- **Serial write lock** — all `ser.write()` calls share a `threading.Lock` to prevent byte interleaving from concurrent threads
- **Thread-safe state flags** — `motors_enabled` and `emergency_stop` guarded by `_state_lock` (MultiThreadedExecutor safe)
- **Cmd_vel timeout** — stop command sent once per timeout event; set outside `_cmd_time_lock` to avoid holding it during the 2ms serial delay
- **Adaptive covariance** — accumulated position/rotation variance uses exponential decay (factor 0.99 by default) to prevent unbounded growth
- **Odometry deduplication** — `/odom` publishes only when firmware data changes; skips duplicate frames at 50Hz sensor timer rate. When unchanged, re-publishes at `odometry.heartbeat_interval` (default 0.5 s) so late-joining subscribers (e.g. web dashboard) receive data within one interval
- **Odometry QoS** — `/odom` uses RELIABLE + TRANSIENT_LOCAL (depth 5) so subscribers that support TRANSIENT_LOCAL receive the last message on connect; heartbeat ensures VOLATILE subscribers (e.g. rosbridge) get a message within `heartbeat_interval`
- **Yaw wraparound** — angular difference uses modular arithmetic to prevent ±2π spikes in covariance accumulation
- **Serial reconnect** — receive thread auto-reconnects after disconnect and re-enables auto-report if firmware rebooted
- **Flash protection** — `set_auto_report_state` uses `forever=False` to avoid writing firmware flash on every startup
