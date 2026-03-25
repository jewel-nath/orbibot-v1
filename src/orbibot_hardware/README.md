# orbibot_hardware

ROS 2 hardware interface for OrbiBot. Bridges the Yahboom ROSMaster V3.0 expansion board
(STM32 firmware) to the ROS 2 ecosystem over USB serial (115200 baud).

The STM32 firmware runs motor PID control and odometry at 100Hz. This package
publishes the sensor data as standard ROS 2 topics and forwards `/cmd_vel` commands
to the firmware. For firmware internals, see
[orbibot_rosmaster_firmware/README.md](../orbibot_rosmaster_firmware/README.md).

---

## Nodes

### hardware_node (`orbibot_hardware_node`)

Publishes sensor data and accepts velocity/PID commands.

#### Subscriptions

| Topic | Type | QoS | Description |
|-------|------|-----|-------------|
| `/cmd_vel` | `geometry_msgs/Twist` | Reliable | Velocity commands forwarded to firmware |
| `/orbibot/pid_params` | `std_msgs/Float32MultiArray` | Default | Motor PID gains `[kp, ki, kd]` — temporary, all motors |
| `/orbibot/yaw_pid_params` | `std_msgs/Float32MultiArray` | Default | Yaw PID gains `[kp, ki, kd]` — temporary |
| `/orbibot/pid_save` | `std_msgs/Float32MultiArray` | Default | Save motor PID to flash `[kp, ki, kd]` — persists across reboot |
| `/orbibot/yaw_pid_save` | `std_msgs/Float32MultiArray` | Default | Save yaw PID to flash `[kp, ki, kd]` — persists across reboot |
| `/orbibot/beep` | `std_msgs/UInt16` | Default | Buzzer: `0`=off, `1`=continuous, `≥10`=on for N ms then auto-off |

#### Publications

| Topic | Type | QoS | Rate | Description |
|-------|------|-----|------|-------------|
| `/odom` | `nav_msgs/Odometry` | Reliable, TRANSIENT_LOCAL (depth 5) | ~20Hz (heartbeat when idle) | Firmware wheel odometry; deduplicated; re-published at `odometry.heartbeat_interval` when unchanged so late joiners (e.g. web GUI) get data |
| `/imu/data` | `sensor_msgs/Imu` | Best Effort (depth 5) | 50Hz | Filtered attitude (orientation) + accel + gyro |
| `/imu/data_raw` | `sensor_msgs/Imu` | Best Effort (depth 5) | ~20Hz (firmware) / 50Hz timer | Raw accel + gyro, no orientation (for imu_filter_madgwick). Firmware sends at 20Hz; node re-publishes at 50Hz timer rate (most recent frame). |
| `/imu/mag` | `sensor_msgs/MagneticField` | Best Effort (depth 5) | ~20Hz (firmware) / 50Hz timer | Magnetometer in Tesla (skipped if all-zero). Same rate note as above. |
| `/orbibot/encoders` | `std_msgs/Int32MultiArray` | Best Effort (depth 5) | ~20Hz (firmware) / 50Hz timer | Raw encoder counts `[FL, BL, FR, BR]` in ticks. Same rate note as above. |
| `/joint_states` | `sensor_msgs/JointState` | Reliable (depth 10) | 50Hz | Wheel positions (rad) for RViz visualization |
| `/orbibot/system_status` | `orbibot_msgs/SystemStatus` | Reliable (depth 10) | 10Hz | Battery voltage, motor state, hardware health |
| `/orbibot/safety_status` | `orbibot_msgs/SafetyStatus` | Reliable (depth 10) | 10Hz | Emergency stop, timeouts, faults |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | Reliable (depth 10) | 10Hz | Standard ROS diagnostics |

#### Services

| Service | Type | Description |
|---------|------|-------------|
| `/orbibot/set_motor_enable` | `orbibot_msgs/SetMotorEnable` | Enable/disable motors |
| `/orbibot/calibrate_imu` | `orbibot_msgs/CalibrateIMU` | **DEPRECATED.** Sends (0,0,0) to firmware (no-op). Use `ros2 run orbibot_localization calibrate_magnetometer` instead. |
| `/orbibot/reset_odometry` | `orbibot_msgs/ResetOdometry` | Reset firmware odometry to `(0,0,0)`; encoder counts unchanged. `reset_pose` field is not supported — firmware always resets to zero. |
| `/orbibot/reset_encoders` | `orbibot_msgs/ResetEncoders` | Reset encoder counts to zero (MCU + node state); odometry unchanged |
| `/orbibot/get_firmware_version` | `orbibot_msgs/GetFirmwareVersion` | Request firmware version from STM32; returns `major`, `minor`, `version_string` |
| `/orbibot/set_mag_calibration` | `orbibot_msgs/SetMagCalibration` | Set magnetometer hard-iron offsets explicitly in µT (`offset_x`, `offset_y`, `offset_z`) |

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
| `control` | `pid_rate_limit` | `0.1` s | Min interval between PID topic updates (max 10 Hz) |
| `rates` | `sensor_rate` | `50.0` Hz | IMU, encoder, joint state publish rate |
| `rates` | `status_rate` | `10.0` Hz | System/safety status publish rate |
| `safety` | `battery_low_threshold` | `11.0` V | Low battery warning level |
| `safety` | `battery_critical_voltage` | `10.5` V | Emergency stop threshold |
| `imu` | `accel_covariance_x/y/z` | `0.01` | Per-axis accel covariance (m/s^2)^2 |
| `imu` | `gyro_covariance_x/y/z` | `0.0025` | Per-axis gyro covariance (rad/s)^2 |
| `imu` | `orientation_covariance` | `0.0025` | Orientation covariance (rad^2) |
| `imu` | `mag_hard_iron_x/y/z` | `0.0` T | Hard-iron bias (permanent magnet offset). Run `calibrate_magnetometer` to compute. |
| `imu` | `mag_soft_iron_scale_x/y/z` | `1.0` | Soft-iron axis scale (ferromagnetic distortion). Run `calibrate_magnetometer` to compute. |
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
# Set motor PID gains (temporary — lost on reboot)
ros2 topic pub --once /orbibot/pid_params std_msgs/msg/Float32MultiArray \
  "data: [0.8, 0.06, 0.5]"

# Set yaw PID gains (temporary)
ros2 topic pub --once /orbibot/yaw_pid_params std_msgs/msg/Float32MultiArray \
  "data: [0.4, 0.0, 0.1]"

# Save motor PID to flash (persists across reboot)
ros2 topic pub --once /orbibot/pid_save std_msgs/msg/Float32MultiArray \
  "data: [0.8, 0.06, 0.5]"

# Save yaw PID to flash (persists across reboot)
ros2 topic pub --once /orbibot/yaw_pid_save std_msgs/msg/Float32MultiArray \
  "data: [0.4, 0.0, 0.1]"
```

## Firmware Version and Magnetometer Calibration

```bash
# Request firmware version from STM32
ros2 service call /orbibot/get_firmware_version orbibot_msgs/srv/GetFirmwareVersion '{}'

# Set explicit magnetometer hard-iron offsets (µT)
ros2 service call /orbibot/set_mag_calibration orbibot_msgs/srv/SetMagCalibration \
  '{offset_x: 5.2, offset_y: -3.1, offset_z: 1.0}'

# Full magnetometer calibration procedure (recommended)
ros2 run orbibot_localization calibrate_magnetometer
```

## Buzzer Examples

```bash
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 200"  # Beep 200ms
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 1"    # Continuous
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 0"    # Off
```

---

## IMU Topic Architecture

hardware_node publishes **three** IMU-related topics. Understanding which topic to use where is critical:

```
hardware_node publishes:
  /imu/data          Firmware complementary filter attitude (orientation + accel + gyro)
                     orientation_covariance = per-axis from yaml config
                     PURPOSE: Debugging/monitoring ONLY
                     ⚠️ NOT consumed by EKF — do NOT add to ekf_params.yaml

  /imu/data_raw      Accel + gyro only (orientation_covariance[0] = -1, meaning "unknown")
                     PURPOSE: Input to imu_filter_madgwick
                     ✅ Madgwick subscribes to this

  /imu/mag           Magnetometer in Tesla (hard+soft iron corrected in Python from yaml)
                     Skipped when all-zero (DRDY not set)
                     PURPOSE: Input to imu_filter_madgwick
                     ✅ Madgwick subscribes to this

imu_filter_madgwick publishes:
  /imu/data_filtered  Fused orientation quaternion (accel + gyro + mag)
                      ✅ EKF subscribes to this (yaw + yaw_rate in relative mode)
```

**Magnetometer correction** is applied in Python (`_publish_mag`) using hard-iron offsets and soft-iron scale factors from `hardware_params.yaml`. The firmware has a 3x3 soft-iron matrix capability (`imu_set_mag_calibration`) but it is not activated during normal operation — Python-side correction is the active path.

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

# Reset odometry (pose only; encoders unchanged)
ros2 service call /orbibot/reset_odometry orbibot_msgs/srv/ResetOdometry '{}'

# Reset encoder counts (odometry unchanged)
ros2 service call /orbibot/reset_encoders orbibot_msgs/srv/ResetEncoders '{}'

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
- **Serial reconnect** — receive thread auto-reconnects after disconnect and re-enables auto-report if firmware rebooted; uses backoff (2s, 3s, …) to give USB/device time to recover
- **Flash protection** — `set_auto_report_state` uses `forever=False` to avoid writing firmware flash on every startup

### Serial dropout after ~60 s (“device reports readiness to read but returned no data”)

If the hardware node works for a minute then enters a reconnect loop with the above error, the usual cause is USB or STM32: cable/contact, power, or STM32 reset. Check: USB cable and port (try another), power supply, and that no other process uses `/dev/motordriver`. The driver now uses reconnect backoff and a short delay after reopen to reduce log spam and give the device time to re-enumerate.
