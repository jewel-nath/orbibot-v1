# LGDXRobot2 — Reference Notes

## Robot Overview

**LGDXRobot2** is an open-source autonomous mobile robot featured on the OpenRobotics blog.
It uses a mechanical (non-mecanum) wheel drive with a Raspberry Pi 5 and the same class of
JGB37-520 geared motors as OrbiBot. It's notable for its clean ROS 2 architecture, well-structured
Nav2 multi-config parameter system, and production-quality autonomous navigation.

**Project site:** https://lgdxrobot.uk/ · **Code:**
[ROS 2](https://github.com/yukaitung/lgdxrobot2-ros2), [MCU firmware](https://github.com/yukaitung/lgdxrobot2-mcu)
**Why it's useful:** Best-in-class Nav2 parameter organization, EKF + IMU Madgwick fusion config,
and clean bringup architecture. Its PID, odometry and IMU handling were compared
against OrbiBot's; the webgui comparison is in [OrbiBot WebGUI vs LGDXRobot2 ChassisTuner](lgdxrobot2-chassistuner.md).

---

## Hardware

| Component | LGDXRobot2 | OrbiBot |
|---|---|---|
| Drive type | Differential (2-wheel) | Mecanum (4-wheel omnidirectional) |
| MCU | STM32F411CEU | STM32F103RCT6 |
| Motor | JGB37-520 (same class) | JGB37-520 (same) |
| SBC | Raspberry Pi 5 | Raspberry Pi 5 (same) |
| IMU | On STM32 board | ICM-20948 on expansion board |
| Communication | USB CDC (serial over USB) | UART serial |

---

## Repository Structure

```
LGDXRobot2/
├── lgdxrobot2-mcu/        STM32F411 firmware (CMake, bare-metal HAL)
└── lgdxrobot2-ros2/       Full ROS 2 workspace
    ├── lgdxrobot2_bringup/
    ├── lgdxrobot2_description/
    ├── lgdxrobot2_msgs/
    └── lgdxrobot2_navigation/
```

Note: `lgdxrobot2-chassistuner` (Qt PID tuner GUI) was removed — OrbiBot has its own webgui.
Webots simulation and cloud agent packages were also removed as not relevant.

---

## Firmware (`lgdxrobot2-mcu/`)

**Toolchain:** CMake + gcc-arm-none-eabi (modern, not Keil)
**MCU:** STM32F411CEU (different from OrbiBot's STM32F103)
**Communication:** USB CDC (virtual serial port)

### Key source files

| File | Purpose |
|---|---|
| `Inc/motor.h` / `Src/motor.c` | Motor PWM control |
| `Inc/imu.h` / `Src/imu.c` | IMU data acquisition |
| `Inc/estop.h` / `Src/estop.c` | Emergency stop logic |
| `Inc/flash.h` / `Src/flash.c` | Parameter persistence to flash |
| `Inc/power.h` / `Src/power.c` | Power management |
| `Inc/configuation.h` | Robot-wide configuration |

**OrbiBot relevance:** The STM32 is different so code isn't directly portable, but the
`estop.c` and `flash.c` patterns are good references for adding those features to OrbiBot firmware.

---

## ROS 2 Packages (`lgdxrobot2-ros2/`)

### `lgdxrobot2_bringup/` — Most Valuable Package

The best-structured bringup package in the references. Key features:

**Launch files:**
- `bringup.launch.py` — main robot bring-up (hardware + sensors)
- `explore.launch.py` — frontier exploration
- `nav.launch.py` — autonomous navigation

**Multi-config Nav2 parameter system** (`param/`):

| Directory | Mode |
|---|---|
| `param/slam/nav2.yaml` | SLAM mapping mode |
| `param/loc/nav2.yaml` | Localization + navigation (DWB) |
| `param/loc-mppi/nav2.yaml` | Localization + MPPI controller |
| `param/loc-rpp/nav2.yaml` | Localization + RPP controller |

This pattern — separate param dirs per operational mode — is the recommended approach for OrbiBot.

**EKF config (`param/ekf.yaml`):**
- Fuses wheel odometry + IMU (Madgwick filtered)
- Uses `imu_filter_madgwick` for pre-processing IMU before EKF
- `imu_filter_madgwick.yaml` — Madgwick filter parameters

**Key EKF design choice:** LGDXRobot2 runs IMU data through a Madgwick filter first, then feeds
the filtered output into robot_localization EKF. This is more robust than feeding raw IMU directly.

**RViz configs:** `rviz/slam.rviz`, `rviz/loc.rviz`, `rviz/default.rviz` — useful starting points.

### `lgdxrobot2_description/`

- `description/lgdxrobot2.urdf` — clean single-file URDF (no xacro)
- `meshes/dae/` — 12 Collada mesh files for all robot parts
- Reference for clean URDF structure and joint definitions

### `lgdxrobot2_msgs/`

Custom messages:
- `msg/AutoTask.msg` — autonomous task definition
- `msg/RobotData.msg` — robot telemetry data structure
- `srv/AutoTaskAbort.srv` — abort action service
- `srv/AutoTaskNext.srv` — next task service

**OrbiBot relevance:** `RobotData.msg` structure is a reference for OrbiBot's `SystemStatus` message design.

### `lgdxrobot2_navigation/`

Launch files for navigation subsystem:
- `bringup_launch.py` — navigation bringup
- `localization_launch.py` — AMCL localization
- `navigation_launch.py` — Nav2 stack
- `slam_launch.py` — slam_toolbox mapping

Clean separation of navigation concerns — each mode has its own launch file.

---

## Nav2 Configuration Highlights

### MPPI config (`param/loc-mppi/nav2.yaml`)
LGDXRobot2 is differential drive so its MPPI config uses `Diff` motion model. For OrbiBot,
change to `Omni` and add `vy_max`. Key values to compare:

```yaml
# LGDXRobot2 MPPI (differential)
motion_model: "Diff"
batch_size: 2000
time_steps: 56
iteration_count: 1
temperature: 0.3
vx_max: 0.5
wz_max: 1.9
```

### Exploration config (`param/explore_node.yaml`)
Uses `explore_lite` (or compatible) frontier explorer. Key params for tuning exploration behavior.

---

## Key Architectural Patterns to Adopt in OrbiBot

| Pattern | Location | OrbiBot action |
|---|---|---|
| Multi-config Nav2 params (slam/, loc/, loc-mppi/) | `lgdxrobot2_bringup/param/` | Adopt this structure in `orbibot_bringup/` |
| Madgwick pre-filter before EKF | `param/imu_filter_madgwick.yaml` + `ekf.yaml` | Consider adding to `orbibot_localization/` |
| Separate nav launch files per mode | `lgdxrobot2_navigation/launch/` | Already partially done in OrbiBot |
| RViz configs per operational mode | `rviz/slam.rviz`, `rviz/loc.rviz` | Add to `orbibot_bringup/rviz/` |

---

## What to Use From This Reference

| Need | File to consult |
|---|---|
| Nav2 multi-mode param structure | `lgdxrobot2_bringup/param/` (all subdirs) |
| MPPI controller params | `lgdxrobot2_bringup/param/loc-mppi/nav2.yaml` |
| EKF + Madgwick fusion setup | `lgdxrobot2_bringup/param/ekf.yaml` + `imu_filter_madgwick.yaml` |
| Clean bringup launch structure | `lgdxrobot2_bringup/launch/bringup.launch.py` |
| Exploration launch | `lgdxrobot2_bringup/launch/explore.launch.py` |
| URDF reference | `lgdxrobot2_description/description/lgdxrobot2.urdf` |
| Custom message design | `lgdxrobot2_msgs/msg/RobotData.msg` |
| Firmware estop/flash patterns | `lgdxrobot2-mcu/Src/estop.c`, `flash.c` |
