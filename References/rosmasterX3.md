# Yahboom RosMaster X3 — Reference Notes

## Robot Overview

The **Yahboom RosMaster X3** is Yahboom's commercial ROS 2 mecanum-wheel robot. It shares the same
hardware core as OrbiBot: same Yahboom ROSMaster V3.0 expansion board (STM32F103RCT6), same
JGB37-520 geared motors, and Raspberry Pi 5. The key mechanical difference is wheel diameter —
X3 uses smaller mecanum wheels vs OrbiBot's 100mm steel mecanum wheels.

**Why it's useful:** The X3 is the upstream reference for OrbiBot's serial protocol, firmware
behavior, mecanum driver, and EKF config. Yahboom's own production driver and firmware are here.

> **Scope note:** The RosMaster codebase supports multiple robot variants — X3, X3 PLUS, X1
> (all mecanum), and R2 (Ackermann steering). **We only care about the X3 variant** (`CARTYPE_X3 = 0x01`).
> When reading any source file, ignore code paths for `X3_PLUS`, `X1`, `R2`, and `Ackman`.
> In the firmware: use `MECANUM_APB` / `MECANUM_CIRCLE_MM` constants (not MAX or MINI variants).
> In ROS 2 packages: use files named `*_X3*` — e.g. `Mcnamu_driver_X3.py`, `base_node_X3.cpp`,
> `yahboomcar_X3.urdf.xacro`, launch files with `_X3` suffix.

---

## Hardware

| Component | X3 | OrbiBot |
|---|---|---|
| MCU | STM32F103RCT6 | STM32F103RCT6 (same) |
| Expansion Board | ROSMaster V3.0 | ROSMaster V3.0 (same) |
| Motor | JGB37-520 | JGB37-520 (same) |
| Wheel diameter | **65 mm** (32.5 mm radius) | **100 mm** (50 mm radius) |
| Wheel separation X (wheelbase) | **160 mm** | **260 mm** |
| Wheel separation Y (track) | **169 mm** | **360 mm** |
| APB `(lx + ly) / 2` in firmware | **164.6 mm** | **310 mm** |
| Encoder CPR | 1320 | 1320 (same) |
| SBC | Raspberry Pi 5 | Raspberry Pi 5 (same) |
| IMU | ICM-20948 + MPU-9250 | ICM-20948 |
| LiDAR | RPLidar A1 | RPLidar A1 (same) |

> **Important:** OrbiBot uses the same ROSMaster V3.0 board and motors as the X3, but on a
> **much larger chassis**. All geometry values (wheel radius, wheelbase, track) are completely
> different. Never copy X3 geometry constants directly — only the firmware protocol, PID logic,
> and kinematics formulas are portable.

---

## Firmware (`yahboom_rosmaster_expansion_board_firmware/`)

**Toolchain:** Keil MDK (uvprojx), STM32F10x standard peripheral library + FreeRTOS
**Pre-built binary:** `output/rosmaster_V3.5.1.hex` — can be flashed directly to OrbiBot's board

### Key source files

| File | Purpose |
|---|---|
| `Source/APP/config.h` | Build flags: IMU enable, auto-report timeout, debug flags |
| `Source/APP/protocol.c/.h` | Serial packet parser and builder |
| `Source/APP/app_mecanum.c/.h` | Mecanum inverse kinematics |
| `Source/APP/app_pid.c/.h` | Motor PID controller |
| `Source/APP/app_bat.c/.h` | Battery ADC reading |
| `Source/BSP/bsp_encoder.c/.h` | Quadrature encoder reading |
| `Source/BSP/bsp_motor.c/.h` | PWM motor output |
| `Source/MEMS/icm20948.c/.h` | ICM-20948 SPI driver |
| `Source/TOOL/tool_pid.c/.h` | PID math utilities |

### Config flags (release build)
- `AUTO_SEND_TIMEOUT = 40` ms → auto-report runs at **25 Hz**
- Both `ENABLE_ICM20948` and `ENABLE_MPU9250` are enabled simultaneously
- `ENABLE_YAW_ADJUST = 1`, `ENABLE_ROLL_PITCH = 0` — yaw corrected, roll/pitch are raw sensor values
- `ENABLE_IWDG = 0` — watchdog disabled in stock firmware
- `ENABLE_FLASH = 1` — PID gains persisted to flash

---

## Serial Protocol

Packet format: `[0xFF][DeviceID][Length][FuncCode][Data...][Checksum]`
- Receive device ID: `0xFC`, Send device ID: `0xFB`
- Checksum: sum of all bytes after header, mod 256

### Function codes (from `Rosmaster_Lib.py` v3.3.9)

| Code | Name | Direction | Data |
|---|---|---|---|
| `0x01` | AUTO_REPORT | TX | Enable/disable streaming |
| `0x02` | BEEP | TX | Beep duration |
| `0x0A` | REPORT_SPEED | RX | Vx, Vy, Vz (int16/1000 m/s) + battery voltage (uint8) |
| `0x0B` | REPORT_MPU_RAW | RX | MPU-9250 raw gyro/accel |
| `0x0C` | REPORT_IMU_ATT | RX | Roll, pitch, yaw (attitude) |
| `0x0D` | REPORT_ENCODER | RX | 4× encoder counts (int32) |
| `0x0E` | REPORT_ICM_RAW | RX | ICM-20948 raw gyro/accel |
| `0x0F` | RESET_STATE | TX | Reset motion state |
| `0x10` | MOTOR | TX | Direct PWM to 4 motors |
| `0x11` | CAR_RUN | TX | Velocity + duration |
| `0x12` | MOTION | TX | Vx, Vy, Vz velocity command |
| `0x13` | SET_MOTOR_PID | TX | Kp, Ki, Kd per motor |
| `0x14` | SET_YAW_PID | TX | Yaw PID gains |
| `0x15` | SET_CAR_TYPE | TX | Car type (X3=0x01, X1=0x04, R2=0x05) |
| `0x50` | REQUEST_DATA | TX | Request specific data once |
| `0x51` | VERSION | RX | Firmware version string |
| `0xA0` | RESET_FLASH | TX | Reset flash to defaults |

---

## Python Driver (`yahboom_rosmaster_firmware_driver/`)

**File:** `Rosmaster_Lib/Rosmaster_Lib.py` — version **V3.3.9**
This is the upstream Python serial driver that OrbiBot's `rosmaster_driver.py` is based on.

Key behaviors:
- Default port: `/dev/myserial` at 115200 baud
- Background receive thread parses incoming packets continuously
- Speed data: signed int16 / 1000.0 → m/s
- Battery: unsigned byte in speed report packet
- Car type must be set at init (`CARTYPE_X3 = 0x01` for X3/OrbiBot)

**OrbiBot difference:** OrbiBot's `rosmaster_driver.py` is a cleaned-up ROS 2 adaptation of this library with additional odometry calculation.

---

## ROS 2 Packages (`src/`)

### Kept (relevant to OrbiBot)

| Package | What it contains | OrbiBot relevance |
|---|---|---|
| `yahboomcar_bringup` | `Mcnamu_driver_X3.py` — the original mecanum ROS 2 driver node; calibration scripts; patrol demos | Primary reference for hardware node behavior and odometry publishing |
| `yahboomcar_base_node` | C++ hardware serial node (`base_node_X3.cpp`) | Alternative C++ implementation of the serial driver |
| `yahboomcar_ctrl` | Joystick teleop (`yahboom_joy_X3.py`), keyboard teleop | Reference for joystick button mapping and velocity scaling |
| `yahboomcar_description` | URDF/xacro + STL meshes for X3 (mecanum variant) | Mecanum wheel placement, joint definitions |
| `yahboomcar_nav` | Nav2 params (DWB/TEB/rtabmap), map files, rviz configs | Navigation baseline — note: uses DWB not MPPI, differential model not omni |
| `yahboomcar_laser` | Obstacle avoidance, laser tracker, warning zone scripts | LiDAR-based behavior reference |
| `yahboomcar_msgs` | Custom messages: `ImageMsg`, `PointArray`, `Position`, `Target`, `TargetArray` | Message format reference |
| `laserscan_to_point_pulisher` | LaserScan → PointCloud2 converter node | Useful for RealSense+LiDAR fusion |
| `robot_pose_publisher` / `_ros2` | Publishes robot pose as `geometry_msgs/Pose` | Simple pose republisher pattern |

### Key file: `Mcnamu_driver_X3.py`
The original mecanum driver node. Subscribes to `/cmd_vel`, sends `MOTION` serial command. Publishes
`/odom` from encoder data using mecanum forward kinematics. This is the direct ancestor of
OrbiBot's `hardware_node.py`.

### Key files: `yahboomcar_nav/`
- `params/dwa_nav_params.yaml` — DWB controller config (differential, `max_vel_y: 0.0`)
- `params/teb_nav_params.yaml` — TEB controller config
- `maps/yahboomcar.pgm/.yaml` — sample saved map

**Note:** Yahboom nav uses `robot_model_type: "differential"` in AMCL and `max_vel_y: 0.0` in DWB.
OrbiBot overrides both to use `OmniMotionModel` and MPPI with `vy_max: 0.5`.

---

## EKF Reference (`robot_localization_ref/`)

Two files extracted from Yahboom's custom `robot_localization` package:

- `ekf_x1_x3.yaml` — EKF params tuned for X1/X3 hardware
- `ekf_x1_x3_launch.py` — launch file for the above

### Key differences vs OrbiBot's EKF config

| Setting | Yahboom X3 | OrbiBot |
|---|---|---|
| Odometry topic | `/odom_raw` | `/odom` |
| EKF frequency | 30 Hz | (check ekf_params.yaml) |
| Odom position fusion | Yes (x, y, yaw) | Velocities only |
| IMU differential | false, relative: true | (check ekf_params.yaml) |
| Process noise (pos) | 0.05 | (check ekf_params.yaml) |

**Notable:** Yahboom fuses both position AND velocity from odometry. OrbiBot currently fuses
velocities only — Yahboom's approach may reduce drift.

---

## What to Use From This Reference

| Need | File to consult |
|---|---|
| Protocol bug / new function code | `yahboom_rosmaster_expansion_board_firmware/Source/APP/protocol.c` |
| Firmware flash (board reset) | `output/rosmaster_V3.5.1.hex` |
| Serial driver behavior | `yahboom_rosmaster_firmware_driver/Rosmaster_Lib/Rosmaster_Lib.py` |
| Mecanum driver node logic | `src/yahboomcar_bringup/yahboomcar_bringup/Mcnamu_driver_X3.py` |
| Nav2 baseline config | `src/yahboomcar_nav/params/dwa_nav_params.yaml` |
| EKF tuning reference | `robot_localization_ref/ekf_x1_x3.yaml` |
| URDF/mesh reference | `src/yahboomcar_description/urdf/yahboomcar_X3.urdf.xacro` |
