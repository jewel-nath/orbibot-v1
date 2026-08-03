# OrbiBot Comprehensive Testing Guide

**Version**: 1.0  
**Last Updated**: 2026-03-02  
**Purpose**: Step-by-step testing procedures for all OrbiBot subsystems

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Firmware Testing](#phase-1-firmware-testing)
3. [Phase 2: Hardware + Firmware Integration](#phase-2-hardware--firmware-integration)
4. [Phase 3: PID Tuning & Calibration](#phase-3-pid-tuning--calibration)
5. [Phase 4: WebGUI Testing](#phase-4-webgui-testing)
6. [Phase 5: Localization Verification](#phase-5-localization-verification)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

- OrbiBot robot with charged 4S LiFePO4 battery (12.8V nominal)
- USB-C cable for STM32 programming
- Micro-USB cable for serial monitoring
- Computer with Ubuntu 22.04+ and ROS 2 Jazzy

### Software Requirements

```bash
# ROS 2 Jazzy
source /opt/ros/jazzy/setup.bash

# PlatformIO for firmware
pip install platformio

# OrbiBot workspace built
cd ~/orbibot_ws
colcon build --symlink-install
source install/setup.bash

# Device permissions
ls -la /dev/motordriver /dev/lidar  # Should show accessible devices
```

### Safety Checklist

- Robot on blocks (wheels free to spin) for initial tests
- Emergency stop accessible
- Clear workspace (2m radius minimum)
- Battery voltage > 11.0V (check with multimeter if unsure)

---

## Phase 1: Firmware Testing

### 1.1 Build and Upload Firmware

```bash
cd src/orbibot_rosmaster_firmware

# Build firmware
~/.platformio-venv/bin/pio run

# Expected output:
# RAM:   [====      ]  ~40% (used ~19,560 bytes from 49,152 bytes)
# Flash: [==        ]  ~15% (used ~38,000 bytes from 262,144 bytes)
```

**Upload Procedure:**

1. Set BOOT0 jumper to HIGH (connect to 3.3V)
2. \
3. Press RESET button on ROSMaster board
4. Run upload command:
  ```bash
   ~/.platformio-venv/bin/pio run --target upload
  ```
5. Set BOOT0 jumper to LOW (connect to GND)
6. Press RESET button again

### 1.2 Serial Communication Test

```bash
# Monitor serial output (115200 baud)
~/.platformio-venv/bin/pio device monitor --baud 115200

# Expected startup messages:
# [OrbiBot] v2.0.0
# [OrbiBot] ICM-20948 WHO_AM_I: 0xEA ✓
# [OrbiBot] Gyro calibration complete
# [OrbiBot] FreeRTOS scheduler started
```

### 1.3 Run Firmware Test Suite

```bash
cd src/orbibot_rosmaster_firmware/tests

# Run all tests
python3 run_all_tests.py --port /dev/motordriver

# Or run individual tests:
python3 test_version.py --port /dev/motordriver      # Firmware version check
python3 test_beep.py --port /dev/motordriver         # Buzzer test
python3 test_encoder.py --port /dev/motordriver      # Encoder counting
python3 test_imu.py --port /dev/motordriver          # IMU data verification
python3 test_motor_speed.py --port /dev/motordriver  # Motor PWM sweep
python3 test_odometry.py --port /dev/motordriver     # Odometry accuracy
python3 test_pid.py --port /dev/motordriver          # PID response
```

### 1.4 Expected Test Results


| Test               | Pass Criteria                             | Common Failures                       |
| ------------------ | ----------------------------------------- | ------------------------------------- |
| `test_version`     | Returns firmware version string           | No serial connection                  |
| `test_beep`        | Audible beep pattern                      | Buzzer wiring, transistor Q1          |
| `test_encoder`     | Counts increase when wheels spun by hand  | Wrong encoder direction, broken wires |
| `test_imu`         | Non-zero gyro/accel values, WHO_AM_I=0xEA | SPI wiring, IMU not seated            |
| `test_motor_speed` | All 4 motors spin smoothly                | Motor driver fault, low battery       |
| `test_odometry`    | Position updates when wheels moved        | Encoder issues, kinematics error      |


### 1.5 Encoder Direction Verification

**Critical**: Verify encoder counting direction matches motor rotation.

```bash
python3 test_encoder.py --port /dev/motordriver --verbose
```

**Manual Check:**

1. Lift robot so wheels are free
2. Spin Front-Left wheel forward (robot would move forward)
3. Encoder count should **increase**
4. Repeat for all 4 wheels

**Direction Correction:**
If any encoder counts backward, check `orbibot_config.h`:

```c
// In include/orbibot_config.h
#define ENCODER_M1_REVERSED  0  // Set to 1 if counting backward
#define ENCODER_M2_REVERSED  0
#define ENCODER_M3_REVERSED  0
#define ENCODER_M4_REVERSED  0
```

---

## Phase 2: Hardware + Firmware Integration

### 2.1 Launch Hardware Node

```bash
# Terminal 1: Launch hardware interface
ros2 launch orbibot_hardware hardware.launch.py

# Check for successful connection:
# [hardware_node]: ROSMaster connected successfully
# [hardware_node]: Auto-report enabled
# [hardware_node]: Motors enabled
```

### 2.2 Verify Topic Publication Rates

```bash
# Terminal 2: Check all topics are publishing at expected rates

ros2 topic hz /odom                          # Expected: ~20 Hz
ros2 topic hz /imu/data_raw                  # Expected: ~50 Hz
ros2 topic hz /imu/mag                       # Expected: ~50 Hz
ros2 topic hz /orbibot/encoders              # Expected: ~50 Hz
ros2 topic hz /joint_states                  # Expected: ~50 Hz
ros2 topic hz /orbibot/system_status         # Expected: ~10 Hz
```

### 2.3 Data Verification Commands

```bash
# Inspect odometry data
ros2 topic echo /odom --once
# Look for:
#   pose.pose.position.x, y, z
#   twist.twist.linear.x, y
#   twist.twist.angular.z

# Inspect IMU data
ros2 topic echo /imu/data_raw --once
# Look for:
#   linear_acceleration.x, y, z (should be ~±9.8 m/s² when stationary)
#   angular_velocity.x, y, z (should be ~0 when stationary)

# Check encoder counts
ros2 topic echo /orbibot/encoders --once
# Format: [FL, BL, FR, BR] in encoder ticks

# Check system status
ros2 topic echo /orbibot/system_status --once
# Look for:
#   battery_voltage (> 11.0V)
#   motor_enabled (True)
#   emergency_stop (False)
```

### 2.4 Motor Control Test

**Place robot on blocks first!**

```bash
# Enable motors (if not auto-enabled)
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: true}'

# Test forward motion (0.1 m/s for 2 seconds)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.1, y: 0.0, z: 0.0}, angular: {z: 0.0}"

# Test strafe right (0.1 m/s)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.0, y: -0.1, z: 0.0}, angular: {z: 0.0}"

# Test rotation (0.5 rad/s)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {z: 0.5}"

# Emergency stop
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {z: 0.0}"
```

### 2.5 Hardware-Firmware Data Consistency

Verify data flows correctly through the stack:


| Data             | Firmware → Hardware     | ROS 2 Topic         | Expected Range |
| ---------------- | ----------------------- | ------------------- | -------------- |
| Wheel velocities | `REPORT_SPEED` (0x0A)   | `/odom/twist`       | ±1000 mm/s     |
| Encoder counts   | `REPORT_ENCODER` (0x0D) | `/orbibot/encoders` | ±2³¹ ticks     |
| IMU raw          | `REPORT_ICM_RAW` (0x0E) | `/imu/data_raw`     | ±32768 ADC     |
| IMU attitude     | `REPORT_IMU_ATT` (0x0C) | `/imu/data`         | ±π rad         |
| Battery          | `REPORT_SPEED` byte 6   | `/system_status`    | 10.5-14.6V     |


---

## Phase 3: PID Tuning & Calibration

### 3.1 Understanding OrbiBot PID Architecture

**Multi-Level Incremental PID System:**

- 3 speed levels with different PID gains
- Interpolation between levels based on current wheel speed
- 100Hz update rate in firmware

### 3.2 Current Default PID Values

```c
// From orbibot_config.h (firmware)
#define PID_KP_LEVEL0  0.8f   // Low speed:    0-100 mm/s
#define PID_KI_LEVEL0  0.06f
#define PID_KD_LEVEL0  0.5f

#define PID_KP_LEVEL1  0.8f   // Medium speed: 100-300 mm/s
#define PID_KI_LEVEL1  0.06f
#define PID_KD_LEVEL1  0.5f

#define PID_KP_LEVEL2  0.8f   // High speed:   300+ mm/s
#define PID_KI_LEVEL2  0.06f
#define PID_KD_LEVEL2  0.5f
```

### 3.3 PID Tuning via ROS 2 Topics

**Temporary tuning (RAM only, lost on reboot):**

```bash
# Format: [t0, t1, t2, kp0, ki0, kd0, kp1, ki1, kd1, kp2, ki2, kd2]
# t0, t1, t2 = speed thresholds in mm/s
# kp, ki, kd = gains for each level

ros2 topic pub --once /orbibot/pid_multilevel std_msgs/msg/Float32MultiArray \
  "data: [100.0, 300.0, 600.0, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5]"
```

**Save to flash (persistent):**

```bash
ros2 topic pub --once /orbibot/pid_save std_msgs/msg/Float32MultiArray \
  "data: [100.0, 300.0, 600.0, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5]"
```

### 3.4 Systematic PID Tuning Procedure

**Step 1: Baseline Test**

```bash
# Place robot on ground, clear path
# Send velocity command and monitor response
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "linear: {x: 0.3, y: 0.0, z: 0.0}, angular: {z: 0.0}" --rate 10

# In another terminal, monitor actual vs target velocity
ros2 topic echo /odom/twist/twist/linear/x
```

**Step 2: Ziegler-Nichols Method**

1. Set Ki = 0, Kd = 0, start with small Kp (0.1)
2. Increase Kp until oscillation occurs (critical gain Kc)
3. Measure oscillation period (Pc)
4. Calculate:
  - Kp = 0.6 × Kc
  - Ki = 2 × Kp / Pc
  - Kd = Kp × Pc / 8

**Step 3: Fine Tuning**


| Symptom                           | Adjustment                   |
| --------------------------------- | ---------------------------- |
| Slow response, steady-state error | Increase Kp                  |
| Oscillation, overshoot            | Decrease Kp, increase Kd     |
| Steady-state error persists       | Increase Ki                  |
| Integral windup (lag after stop)  | Decrease Ki, add anti-windup |
| Noisy/jittery motion              | Decrease Kd, add filtering   |


### 3.5 Exact PID Calculations

**Incremental PID Formula (firmware implementation):**

```
ΔOut = Kp × (Ek - Ek-1) + Ki × Ek + Kd × (Ek - 2×Ek-1 + Ek-2)
Out_k = Out_k-1 + ΔOut
```

Where:

- Ek = error at time k (target - actual)
- Out = PWM output (0-3600)
- Gains are multiplied by 1000 in protocol (0.8 → 800)

**Example Calculation:**

```
Target: 300 mm/s
Actual: 280 mm/s
Ek = 300 - 280 = 20 mm/s

Previous error Ek-1 = 25 mm/s
Ek-2 = 30 mm/s

With Kp=0.8, Ki=0.06, Kd=0.5:
ΔOut = 0.8×(20-25) + 0.06×20 + 0.5×(20-2×25+30)
     = 0.8×(-5) + 0.06×20 + 0.5×0
     = -4 + 1.2 + 0
     = -2.8 PWM units
```

### 3.6 Yaw PID Tuning (Rotation Control)

Separate PID for heading hold during rotation:

```bash
# Set yaw PID
ros2 topic pub --once /orbibot/yaw_pid_params std_msgs/msg/Float32MultiArray \
  "data: [1.0, 0.1, 0.2]"  # [Kp, Ki, Kd]
```

---

## Phase 4: WebGUI Testing

### 4.1 Launch WebGUI Stack

```bash
# Terminal 1: rosbridge + WebRTC server
ros2 launch orbibot_webgui webgui.launch.py

# Terminal 2: Robot base
ros2 launch orbibot_bringup robot.launch.py

# Terminal 3: Frontend dev server
cd src/orbibot_webgui/frontend
npm run dev
```

### 4.2 WebGUI Data Verification Checklist

Open browser to `http://localhost:5173` and verify:

#### Connection Panel (Top Right)

- ROS Status: **Connected** (green)
- WebRTC Status: **Connected** (if camera enabled)
- No error toasts appearing

#### Telemetry Panel (Left Side)

- **Battery Gauge**
  - Voltage displayed matches `ros2 topic echo /orbibot/system_status`
  - Percentage calculated correctly: `(V - 10.5) / (14.6 - 10.5) × 100%`
  - Color changes: Green (>12V), Yellow (11-12V), Red (<11V)
- **Encoder Display**
  - Values update when robot moves
  - FL, BL, FR, BR match `/orbibot/encoders` topic
  - Direction signs correct (positive = forward)
- **IMU Widget**
  - Roll, Pitch, Yaw angles displayed
  - Values match `ros2 topic echo /imu/data`
  - Yaw updates when robot rotates
- **Odometry Display**
  - X, Y position updates
  - Linear velocity matches commanded velocity
  - Angular velocity matches rotation
- **System Health**
  - CPU % reasonable (< 80%)
  - RAM usage displayed
  - Temperature < 70°C
  - Disk usage < 90%

#### Visualization Panel (Center)

- **LiDAR View**
  - Scan points visible when robot stationary
  - Points update when obstacles move
  - Clear/warning/emergency zones color-coded
  - Min obstacle distance displayed
- **Map View** (when SLAM running)
  - Occupancy grid displays
  - Robot pose overlay correct
  - Map updates as robot explores

#### Control Panel (Right Side)

- **Mecanum Controller**
  - All 9 directional buttons work
  - Stop button immediately halts robot
  - Speed slider limits max velocity
- **PID Tuning Panel**
  - Current values displayed
  - Input validation works (gains 0-10, thresholds 0-1000)
  - Save to flash button functional
  - Changes take effect immediately

### 4.3 WebGUI Control Testing

**Test Sequence:**

1. Click **Forward** button → Robot moves forward
2. Click **Stop** → Robot stops immediately
3. Click **Strafe Right** → Robot moves sideways
4. Click **Rotate CW** → Robot rotates clockwise
5. Adjust speed slider to 50% → Verify slower motion
6. Press **Spacebar** → Emergency stop works
7. Use **WASD keys** → Keyboard teleop functional

### 4.4 WebGUI PID Tuning via UI

1. Navigate to PID Tuning panel
2. Modify Level 0 Kp: 0.8 → 1.0
3. Click **Apply**
4. Test robot motion → Should be more responsive
5. If oscillation occurs, reduce Kp
6. Click **Save to Flash** when satisfied

---

## Phase 5: Localization Verification

### 5.1 Launch Localization Stack

```bash
# Terminal 1: Robot base
ros2 launch orbibot_bringup robot.launch.py

# Terminal 2: Localization (Madgwick + EKF)
ros2 launch orbibot_localization localization.launch.py
```

### 5.2 Verify Data Flow

```bash
# Check all localization topics
ros2 topic list | grep -E "(imu|odometry|ekf)"

# Expected:
# /imu/data_filtered
# /imu/data_raw
# /imu/mag
# /odometry/filtered
```

### 5.3 Topic Rate Verification

```bash
ros2 topic hz /imu/data_raw           # ~50 Hz (from hardware)
ros2 topic hz /imu/data_filtered      # ~50 Hz (from Madgwick)
ros2 topic hz /odometry/filtered      # ~20 Hz (from EKF)
ros2 topic hz /tf                     # ~50 Hz
```

### 5.4 Data Quality Checks

**IMU Data Quality:**

```bash
ros2 topic echo /imu/data_raw --once

# When robot is stationary:
# linear_acceleration.z ≈ 9.8 m/s² (gravity)
# linear_acceleration.x, y ≈ 0
# angular_velocity.x, y, z ≈ 0 (small noise OK)
```

**Madgwick Filter Output:**

```bash
ros2 topic echo /imu/data_filtered --once

# orientation quaternion should be valid (normalized)
# No NaN or Inf values
```

**EKF Output:**

```bash
ros2 topic echo /odometry/filtered --once

# Check covariance matrix values are reasonable
# pose.covariance[0] (x variance) should grow slowly
# pose.covariance[35] (yaw variance) should be small (~0.01)
```

### 5.5 TF Tree Verification

```bash
# Generate TF tree PDF
ros2 run tf2_tools view_frames

# Expected tree:
# map (if SLAM running)
# └── odom
#     └── base_footprint
#         └── base_link
#             ├── lidar_link
#             ├── imu_link
#             └── camera_link
```

### 5.6 Localization Accuracy Test

**Straight Line Test:**

1. Place robot at known position (mark on floor)
2. Reset odometry: `ros2 service call /orbibot/reset_odometry std_srvs/srv/Empty`
3. Drive forward 1 meter:
  ```bash
   ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
     "linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {z: 0.0}"
  ```
4. Wait 5 seconds, then stop
5. Check `/odometry/filtered` position vs actual position
6. **Acceptable drift**: < 5% (5cm over 1m)

**Rotation Test:**

1. Reset odometry
2. Rotate 360 degrees:
  ```bash
   ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
     "linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {z: 0.5}"
  ```
3. Wait ~12 seconds (2π / 0.5 ≈ 12.6s)
4. Stop and check yaw in `/odometry/filtered`
5. **Acceptable error**: < 5 degrees

### 5.7 EKF Diagnostics

```bash
# Check EKF health
ros2 topic echo /diagnostics

# Look for:
# - Status: OK (not ERROR or WARN)
# - No "Failed to meet update rate" messages
# - All sensor inputs valid
```

---

## Troubleshooting

### Firmware Issues


| Symptom                     | Cause              | Solution                                |
| --------------------------- | ------------------ | --------------------------------------- |
| Upload fails                | BOOT0 not HIGH     | Set BOOT0=HIGH, press RESET             |
| No serial output            | Wrong baud rate    | Use 115200 baud                         |
| WHO_AM_I fails (not 0xEA)   | IMU not connected  | Check SPI2 wiring (PB12-PB15)           |
| Encoder counts don't change | Wrong direction    | Check encoder wiring, reverse in config |
| Motors don't spin           | Motors not enabled | Send enable command or auto-enable      |


### Hardware Issues


| Symptom                | Cause                | Solution                     |
| ---------------------- | -------------------- | ---------------------------- |
| /odom not publishing   | Serial disconnected  | Check /dev/motordriver       |
| IMU data all zeros     | Madgwick not running | Start localization.launch.py |
| High latency on topics | USB bandwidth        | Use USB 3.0 port, not hub    |
| Motor stuttering       | PID too aggressive   | Reduce Kp, increase Kd       |


### Localization Issues


| Symptom                          | Cause                       | Solution                         |
| -------------------------------- | --------------------------- | -------------------------------- |
| Yaw drifts over time             | Expected — no absolute heading reference since the magnetometer was removed | Bound it: tune Madgwick `zeta` (gyro bias), and let SLAM/AMCL correct via `map → odom`. Measure the drift rate rather than chasing zero |
| Position jumps                   | Wheel slip                  | Reduce acceleration, check floor |
| EKF "Failed to meet update rate" | CPU overload                | Reduce EKF frequency to 20Hz     |
| TF extrapolation errors          | Timing mismatch             | Check sensor timestamps          |


### WebGUI Issues


| Symptom                          | Cause                 | Solution                      |
| -------------------------------- | --------------------- | ----------------------------- |
| "Failed to connect to rosbridge" | Server not running    | Launch webgui.launch.py       |
| No data in panels                | Topics not publishing | Check robot.launch.py running |
| Camera feed black                | WebRTC not connected  | Check use_video:=true         |
| High latency                     | Network issue         | Use wired connection          |


---

## Quick Reference: Essential Commands

```bash
# Full system startup
ros2 launch orbibot_bringup robot.launch.py
ros2 launch orbibot_localization localization.launch.py
ros2 launch orbibot_webgui webgui.launch.py

# Topic monitoring
ros2 topic hz /odom /imu/data_filtered /scan
ros2 topic echo /orbibot/system_status

# Motor control
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: true}'
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "linear: {x: 0.2}, angular: {z: 0.0}"

# PID tuning
ros2 topic pub --once /orbibot/pid_multilevel std_msgs/msg/Float32MultiArray \
  "data: [100.0, 300.0, 600.0, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5]"
ros2 topic pub --once /orbibot/pid_save std_msgs/msg/Float32MultiArray \
  "data: [100.0, 300.0, 600.0, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5, 0.8, 0.06, 0.5]"

# Reset and diagnostics
ros2 service call /orbibot/reset_odometry std_srvs/srv/Empty
ros2 topic echo /diagnostics
ros2 run tf2_tools view_frames
```

---

## Sign-Off Checklist

Before declaring OrbiBot ready for autonomous operation:

- All firmware tests pass
- Hardware node connects without errors
- All topics publishing at expected rates
- Encoder directions verified correct
- PID tuned for smooth motion (no oscillation)
- WebGUI displays all data correctly
- Keyboard/joystick control responsive
- EKF maintains accurate pose (< 5% drift)
- SLAM builds clean map (if equipped)
- Emergency stop functional

