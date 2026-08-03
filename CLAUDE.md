# OrbiBot

Mecanum-wheeled indoor robot. ROS 2 Jazzy on a **Beelink SER5 Pro**, motor
control on a Yahboom ROSMaster V3.0 (STM32F103RCT6) over serial.

> ⚠️ **Migration in progress — 2026-08-03.** The Raspberry Pi 5 that ran this
> stack saturated all four cores under any real load and has been replaced.
> **The Beelink is on a bench, not on the robot.** Nothing is wired to it: no
> motor board, no LiDAR, no camera, and ROS 2 is not installed yet.
>
> So **commands here do not currently move wheels** — but that changes the
> moment the hardware is plugged in, and the safety rules apply from that
> moment. Read `.claude/rules/robot-safety.md` before commanding motion or
> flashing firmware. Setup sequence: [docs/operations/computer-setup.md](docs/operations/computer-setup.md).
>
> The Pi's state is preserved on the `raspberry_pi` branch. Do not delete it.
> **Every CPU-derived tuning value in this repo is void** — see the roadmap.

---

## Find things

Documentation sits **beside the code it describes**. `docs/` holds only what has
nowhere else to live — why the system is shaped this way, what is planned, what
was measured, and how to learn it. Start at [docs/README.md](docs/README.md).

| Looking for | Read |
|---|---|
| **Setting up the new computer** | [docs/operations/computer-setup.md](docs/operations/computer-setup.md) — power, ROS 2, build, mounting |
| **What to build next** | [docs/plan/roadmap.md](docs/plan/roadmap.md) — phases and gates |
| **What is broken** | `src/<pkg>/<pkg>-issue.md`; [docs/moc/backlog-moc.md](docs/moc/backlog-moc.md) maps them |
| A package's API | `src/<pkg>/README.md` |
| A package's orientation and open items | `docs/packages/<pkg>.md` |
| How the system fits together | [docs/architecture/system-overview.md](docs/architecture/system-overview.md) |
| Who is allowed to drive the robot | [docs/architecture/command-pipeline.md](docs/architecture/command-pipeline.md) |
| Dashboard architecture and CPU budget | [docs/architecture/dashboard-design.md](docs/architecture/dashboard-design.md) |
| Board pinout, timers, peripherals | [docs/hardware/rosmaster-board.md](docs/hardware/rosmaster-board.md) |
| What hardware is actually fitted | [docs/hardware/inventory.md](docs/hardware/inventory.md) |
| Bring-up and test procedures | [testing-guide.md](testing-guide.md) |
| What has been verified on hardware, and when | `src/orbibot_rosmaster_firmware/test-report.md` |
| Learning a subsystem from zero | [docs/learn/learn-moc.md](docs/learn/learn-moc.md) — 71 lessons |

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
| `orbibot_agent` | ament_python | Multi-LLM agent, MCP server, CLI, 62 tools |
| `orbibot_teleop` | ament_python | Gamepad teleop — **dormant**, teleop is web-only |

Details: [docs/moc/packages-moc.md](docs/moc/packages-moc.md).

**Deleted, do not recreate:** `orbibot_ai` and `orbibot_mcp_server` (replaced
by `orbibot_agent`). Ignore stale references in old notes.

**Deleted, but re-openable:** `orbibot_gazebo`. It went on the reasoning that
"the Pi is the robot" — a Pi could not run a simulator. The Beelink can
(Ryzen 7 + Vega iGPU, headless via `gz sim -s`). The decision stands until
someone needs it; see *Optional — Simulation* in the roadmap. Do not recreate
it speculatively.

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
`platformio.ini` so the robot's own computer can build it:

```bash
cd src/orbibot_rosmaster_firmware
~/.platformio-venv/bin/pio run                  # build first, always
~/.platformio-venv/bin/pio run --target upload  # needs BOOT0 — see the rules file
~/.platformio-venv/bin/pio device monitor       # 115200
```

> PlatformIO lives in its own venv — `~/.platformio-venv/bin/pio`, installed
> 2026-08-03. The Pi used `~/.platformio/penv/bin/pio`; that path is gone.

```bash
# base: description + hardware + LiDAR + EKF
ros2 launch orbibot_bringup robot.launch.py

# mapping, or exploration instead
ros2 launch orbibot_bringup mapping.launch.py
ros2 launch orbibot_bringup exploration.launch.py

# navigation against a saved map
ros2 launch orbibot_navigation navigation.launch.py map:=$HOME/maps/my_map.yaml

# web dashboard: rosbridge :9090 + WebRTC :8081
ros2 launch orbibot_webgui webgui.launch.py

# firmware test suite (serial, no ROS needed)
cd src/orbibot_rosmaster_firmware/tests && python3 run_all_tests.py --port /dev/motordriver
```

Frontend lives in `src/orbibot_webgui/frontend` — `npm run build` for a served
bundle; do not run the Vite dev server on the robot.

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
- **Maintainer**: Jewel Nath <jewel.nath@orbitax.com>

Full detail in `.claude/rules/`. Longer reference material — node templates, QoS
profiles, test patterns — lives in skills and loads on demand.

---

## Hardware, in one table

| | |
|---|---|
| Compute | Beelink SER5 Pro — Ryzen 7 PRO 5800H, 8C/16T, 11.6 GiB, x86_64 |
| Compute power | 12.8 V → RBD-2767 boost → 19 V; 10 A fuse on the **input** side |
| Wheel radius | 50 mm (100 mm mecanum, ABBA) |
| Wheelbase × track | 260 × 360 mm; footprint 350 × 250 mm; ~6 kg — **re-measure after mounting the Beelink** |
| Encoders | 1320 CPR (11 PPR × 30:1 × 4) |
| Motors | JGB37-520, 30:1, 333 RPM no-load |
| Battery | 4S LiFePO4 — 12.8 V nominal, 11.0 V warning, 10.5 V cutoff |
| IMU | ICM-20948 on SPI2, ±500 dps, ±2 g |
| LiDAR | RPLidar A1 → `/scan` 10 Hz on `/dev/lidar` |
| Board link | 115200 baud on `/dev/motordriver` |

Everything else — pinout, timers, power rails, spare capacity:
[docs/hardware/](docs/hardware/).

---

## Working here

1. Read `docs/packages/<pkg>.md` **and** `src/<pkg>/README.md` before touching a
   package
2. After **any** change — added, changed, or deleted — ask whether it made a
   document untrue, and fix it. `.claude/rules/docs-sync.md` has the map; a
   `Stop` hook interrupts if code moved and no docs did
3. Commit per logical unit, with the reasoning — not batched
4. Report measurements as numbers, not adjectives, and write them down with the
   date and the robot's state

Skills in `.claude/skills/` are auto-discovered and load only when used.
