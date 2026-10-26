# OrbiBot

Mecanum-wheeled indoor robot. ROS 2 Jazzy on a Raspberry Pi 5, motor control on
a Yahboom ROSMaster V3.0 (STM32F103RCT6) over serial.

**Claude Code runs on the robot's own Pi**, wired to the motor board and the
LiDAR. Commands here move real wheels — read `.claude/rules/robot-safety.md`
before commanding motion or flashing firmware.

---

## Find things

Start at [README.md](README.md) for what the robot is, and
[docs/README.md](docs/README.md) for the documentation map. Documentation sits
**beside the code it describes**; `docs/` holds what belongs to the robot as a
whole.

| Looking for | Read |
|---|---|
| **What works, what was tested, what is wrong** | [docs/status.md](docs/status.md) |
| **What is broken in a package** | `src/<pkg>/known-issues.md` |
| A package's API and status | `src/<pkg>/README.md`; the list is [docs/packages.md](docs/packages.md) |
| How the system fits together | [docs/architecture/system-overview.md](docs/architecture/system-overview.md) |
| Who is allowed to drive the robot | [docs/architecture/command-pipeline.md](docs/architecture/command-pipeline.md) |
| Dashboard architecture and CPU budget | [docs/architecture/dashboard-design.md](docs/architecture/dashboard-design.md) |
| Board pinout, timers, peripherals | [docs/hardware/rosmaster-board.md](docs/hardware/rosmaster-board.md) |
| What hardware is actually fitted | [docs/hardware/README.md](docs/hardware/README.md) |
| Setting up and launching | [docs/getting-started.md](docs/getting-started.md), [docs/operations/running.md](docs/operations/running.md) |
| Bring-up and test procedures | [docs/testing/README.md](docs/testing/README.md) |
| What has been verified on hardware, and when | `src/orbibot_rosmaster_firmware/test-report.md` |
| Learning a subsystem from zero | [docs/learn/README.md](docs/learn/README.md) — 70 lessons |

**Source of truth**: the code. If a note disagrees with it, the note is a bug —
fix it.

---

## Packages

| Package | Build | Owns |
|---|---|---|
| `orbibot_rosmaster_firmware` | PlatformIO | STM32: PID, encoders, IMU, odometry, serial protocol |
| `orbibot_hardware` | ament_python | Serial bridge → `/odom`, `/imu/*`, `/joint_states` |
| `orbibot_msgs` | ament_cmake | Custom messages and services |
| `orbibot_description` | ament_cmake | URDF/Xacro, meshes, RViz |
| `orbibot_sensors` | ament_python | RPLidar A1, RealSense, obstacle detector |
| `orbibot_localization` | ament_python | Madgwick + EKF → `odom → base_footprint` |
| `orbibot_slam` | ament_python | slam_toolbox → `/map` + `map → odom` |
| `orbibot_navigation` | ament_cmake | Nav2 params (map and SLAM variants), maps |
| `orbibot_exploration` | ament_python | BFS frontier explorer |
| `orbibot_bringup` | ament_python | Cross-package launch orchestration |
| `orbibot_webgui` | ament_python | rosbridge + WebRTC backend, React frontend |
| `orbibot_agent` | ament_python | Multi-LLM agent, MCP server, CLI, 58 tools |
| `orbibot_teleop` | ament_python | Gamepad teleop — **dormant**, teleop is web-only |

Details: [docs/packages.md](docs/packages.md).

**Deleted, do not recreate:** `orbibot_gazebo` (the Pi is the robot),
`orbibot_ai` and `orbibot_mcp_server` (replaced by `orbibot_agent`). Ignore
stale references in old notes.

---

## Build and run

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install                              # everything
colcon build --symlink-install --packages-select <pkg>      # one package
colcon build --symlink-install --packages-up-to <pkg>       # + dependents
source install/setup.bash
```

`orbibot_rosmaster_firmware` carries a `COLCON_IGNORE` — it is a PlatformIO
project and is never built by colcon. The toolchain is pinned in
`platformio.ini` so the Pi can build it:

```bash
cd src/orbibot_rosmaster_firmware
~/.platformio/penv/bin/pio run                  # build first, always
~/.platformio/penv/bin/pio run --target upload  # needs BOOT0 — see the rules file
~/.platformio/penv/bin/pio device monitor       # 115200
```

```bash
# base: description + hardware + EKF + LiDAR
ros2 launch orbibot_bringup robot.launch.py

# mapping, or exploration instead (start the base first)
ros2 launch orbibot_bringup mapping.launch.py
ros2 launch orbibot_bringup exploration.launch.py

# navigation against a saved map
ros2 launch orbibot_navigation navigation.launch.py map_file:=$HOME/maps/my_map.yaml

# web dashboard: rosbridge :9090 + WebRTC :8081
ros2 launch orbibot_webgui webgui.launch.py

# firmware test suite (serial, no ROS needed)
cd src/orbibot_rosmaster_firmware/tests && python3 run_all_tests.py --port /dev/motordriver
```

Frontend lives in `src/orbibot_webgui/frontend` — `npm run build` for a served
bundle; do not run the Vite dev server on the Pi.

Handy scripts: `.claude/scripts/preflight.sh` before operating,
`safety.sh` to cross-check firmware limits against the ROS 2 config.

---

## Conventions

- **Base frame is `base_footprint`**, never `base_link`
- **TF chain**: `map → odom → base_footprint → base_link → sensor_links`.
  Exactly one node may publish `map → odom`
- **Odometry**: `/odom` is raw wheel odometry; Nav2 and consumers use
  `/odometry/filtered` from the EKF
- **No magnetometer.** Removed 2026-04-28 — indoor iron and motor currents made
  heading worse. Madgwick runs `use_mag: false`, EKF yaw is relative, and drift
  is corrected by SLAM/AMCL. Do not propose bringing it back
- **Teleop is web dashboard only.** `orbibot_teleop` stays as a
  network-independent fallback; do not wire it up
- **Topics**: standard ROS 2 / Nav2 names stay flat (`/cmd_vel`, `/scan`,
  `/odom`); OrbiBot-specific topics take the `/orbibot/` prefix
- **Naming**: `PascalCase` classes, `snake_case` functions and variables,
  `UPPER_SNAKE_CASE` module-level constants, `_single_underscore` for private.
  Files `snake_case.py` / `snake_case.c`, docs `kebab-case.md`
- **Launch messages**: `[PackageName] Description — key: value`
- **Single-package launches** start only their own nodes; cross-package
  composition belongs in `orbibot_bringup`

Full detail in `.claude/rules/`.

---

## Hardware, in one table

| | |
|---|---|
| Wheel radius | 50 mm (100 mm mecanum, ABBA) |
| Wheelbase × track | 260 × 360 mm; footprint 350 × 250 mm; ~6 kg |
| Encoders | 1320 CPR (11 PPR × 30:1 × 4) |
| Motors | JGB37-520, 30:1, 333 RPM no-load |
| Battery | 4S LiFePO4 — 12.8 V nominal, 11.0 V warning, 10.5 V cutoff |
| IMU | ICM-20948 on SPI2, ±500 dps, ±2 g |
| LiDAR | RPLidar A1 → `/scan` (nominal 5.5 Hz) on `/dev/lidar` |
| Board link | 115200 baud on `/dev/motordriver` |

Everything else — pinout, timers, power rails, spare capacity:
[docs/hardware/](docs/hardware/).

---

## Working here

1. Read `src/<pkg>/README.md` and `src/<pkg>/known-issues.md` before touching a
   package
2. After **any** change — added, changed, or deleted — ask whether it made a
   document untrue, and fix it. `.claude/rules/docs-sync.md` has the map; a
   `Stop` hook interrupts if code moved and no docs did
3. Commit per logical unit, with the reasoning — not batched
4. Report measurements as numbers, not adjectives, and write them down with the
   date and the robot's state

