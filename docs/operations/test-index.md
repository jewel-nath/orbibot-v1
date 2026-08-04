---
title: "Test Index"
type: operations
tags:
  - operations
  - testing
---

# Test index — what to run, and what it said last time

One table per question: **how do I test this**, **when was it last run**, **what
did it say**. Procedures live in [[testing-guide]]; live hardware results live in
`test-report.md`. This is the index over both.

> **This file lists what to _run_. [[physical-checks]] lists what to _look at_** —
> the claims software cannot verify about itself: which wheel M4 is, whether the
> LiDAR faces forward, what the wheel radius is under load. A test can pass
> against a wrong assumption, which is exactly what that list exists to catch.

**Update the "last run" column when you run something.** A test whose last
result nobody recorded is a test nobody can trust.

---

## Needs no robot

Runs anywhere, any time. If these are red, fix them before touching hardware.

| What | Command | Last run | Result |
|---|---|---|---|
| **Hardware unit tests** — driver protocol, node logic, launch file | `python3 -m pytest src/orbibot_hardware/tests/ -q` | 2026-08-04 | **82 passed** in directory, reverse and per-file order |
| **Protocol table agreement** — firmware vs driver vs test harness | `python3 -m pytest src/orbibot_rosmaster_firmware/tests/test_protocol_table_agreement.py -q` | 2026-08-04 | **9 passed**; caught `SET_MOTOR = 0x09` when reintroduced |
| **Workspace build** | `colcon build --symlink-install` | 2026-08-04 | 12 packages clean, 17.9 s |
| **Firmware build** | `cd src/orbibot_rosmaster_firmware && ~/.platformio-venv/bin/pio run` | 2026-08-03 | 24.7 KB flash (9.7 %), 21.6 KB RAM (45.1 %), 89 s |
| **Frontend build** | `cd src/orbibot_webgui/frontend && npm run build` | 2026-08-03 | 816 K `dist/` |
| **Firmware/ROS limit cross-check** | `.claude/scripts/safety.sh` | — | not recorded |
| ~~`test_motor_direction.py`~~ | — | — | **withdrawn 2026-08-04** — used a function code the firmware does not implement, then asked a human to confirm. FW-ISSUE-12 |

> Run the unit tests as a **directory**, and occasionally in a different order.
> Per-file green is not green — see [[field-notes]], *Testing traps*.

---

## Needs the board, but no motion

Robot can be anywhere. Motors stay disarmed.

| What | Command | Last run | Result |
|---|---|---|---|
| **Preflight** — devices, nodes, battery | `.claude/scripts/preflight.sh` | — | not recorded |
| **IMU axis convention** — is the sensor aligned with the chassis? | `imu_sequence.py` (camera up/down + clockwise/anticlockwise), then `imu_base_frame.py` | 2026-08-04 | ❗ **The IMU is mounted 90° out.** `imu_joint` said `rpy="0 0 0"`; now `1.5707963`. Proven 3 ways, verified end to end — §9.9, DESC-2 |
| **Stationary IMU** — noise, gyro bias, yaw drift (Phase 4.1 + roadmap 1.3) | `ros2 run orbibot_localization measure_imu_noise --ros-args -p duration:=600.0` | 2026-08-04 | 29977 samples/10 min. \|a\|/g = **1.0002** ✅. Yaw drift **+0.547 °/min** — 83 % of it is gyro Y bias through a **0.94° mounting tilt**, not the gyro. `test-report.md` §9.7, LOC-1 |
| **Stack health** — all topic rates | `/robot-status` | 2026-08-04 18:05 | ✅ full `robot.launch.py`: `/imu/data_raw`, `/joint_states`, `/odometry/filtered` all **50.00 Hz**, `/scan` 8.10 Hz, `hardware_node` 9.75 % |
| **Firmware report rate** — below ROS, no stack running | `python3 .claude/scripts/rate_decay_log.py -w 20 -d 40` | 2026-08-04 17:18 | **49.98 Hz** on all five report types at 2 h 41 min board uptime; battery 12.5 V. Firmware exonerated |
| **Sensor rate under `/cmd_vel` load** — HW-BUG-8 regression guard | `topic_rate_log.py`, then `ros2 topic pub -r 20 /cmd_vel …` (see hardware-issue.md) | 2026-08-04 18:05 | **50.04 Hz under load** ✅ — was 32.4 Hz before the executor fix; node CPU 60.4 % → 10.1 % |
| **cmd_vel arbitration** — priorities, timeouts, e-stop | `python3 .claude/scripts/test_cmd_vel_arbitration.py` | 2026-08-04 18:05 | **8/8**; all sources silent → stop in **286 ms**. Re-run after the executor change |
| **Single writer on `/cmd_vel`** | `ros2 topic info /cmd_vel` | 2026-08-04 | Publisher count **1** (twist_mux), type `Twist` |
| **Active source reporting** | `ros2 topic echo /orbibot/cmd_vel_source` while publishing to an input | 2026-08-04 | tracks `idle` → `web` → `estop` → `idle` |
| **Teardown leaves nothing** | `.claude/scripts/stop.sh` | 2026-08-04 | clean; serial devices released |
| **Firmware protocol suite** — 17 scripts | `cd src/orbibot_rosmaster_firmware/tests && python3 run_all_tests.py --port /dev/motordriver` | 2026-04-19 | see `test-report.md` §8.A |
| **Encoder comms** | `.claude/scripts/encoder.sh` | — | not recorded |

---

## Needs the robot elevated — wheels free

**Ask the operator to put the robot on a stool, then wait.** Valid for
direction, sign and PID step response. **Not** valid for distance, drift or
traction.

| What | Command / section | Last run | Result |
|---|---|---|---|
| **Wheel direction + mecanum kinematics** | `.claude/scripts/motor.sh`, or `test_kinematics.py` directly | 2026-04-19 | all four sign patterns correct — `test-report.md` §6 |
| **Command timeout (2 s)** | `test_safety.py` | 2026-04-19 | motors stop 2.12 s after last command |
| **Velocity clamp** | `test_motor_max_speed.py` | 2026-04-28 | 1023 mm/s peak on a 3000 mm/s command |
| **Per-motor max speed** | `test_motor_max_speed.py` | 2026-04-28 | **M4 runs 12–15 % slow** — FW-ISSUE-4, open |
| **Power rail under motor load (P-3/P-5)** | `test-report.md` §9.6 | 2026-08-03 | P-5 pass, no brown-out. **P-3 still unanswered** — needs traction load |

---

## Needs the robot on the ground, ≥ 2 m clear

**Nothing here has been done on this robot yet.** Every motion number on record
was taken wheels-free, which cannot prove distance, drift or traction.

Blocked on Phase 0.8 — mounting the Beelink changes mass and centre of gravity,
so measuring first means measuring twice.

| What | Roadmap | Gate |
|---|---|---|
| Wheel radius / encoder CPR — drive a measured 2 m | 1.1 | odometry error **< 3 %** both directions |
| Rotation — 10 × 360° in place | 1.2 | accumulated yaw error **< 5°** |
| Yaw drift, stationary, 10 min | 1.3 | recorded — replaces the magnetometer |
| Forward/backward asymmetry | 1.4 | agree within **5 %** |
| Accel X/Y scale under known acceleration | 1.5 | `\|a\|` within **1 %** of g, all axes |
| PID re-tune under the new mass | 1.6 | — |
| **Pull the wifi mid-drive** | 2.x | **the robot stops.** The test that matters |
| Closed 4 m × 4 m loop | 4.3 | final error **< 5 %** of path length |

---

## Where results are written

| Kind of result | Goes in |
|---|---|
| A number measured on hardware | `src/orbibot_rosmaster_firmware/test-report.md`, dated section |
| A finding — new, fixed, or worse | `src/<pkg>/<pkg>-issue.md` |
| A rate or CPU baseline | [[baseline-results]] |
| Something non-obvious you learned | [[field-notes]] |
| **The "last run" column above** | here, every time |

Record the **conditions**, not just the number: robot elevated or on the ground,
which firmware, how many samples, battery on charge or not. A power test run
with the charger connected has already had to be thrown away once.

## Related

[[testing-guide]] · [[roadmap]] · [[field-notes]] · [[baseline-results]] ·
`src/orbibot_rosmaster_firmware/test-report.md` · `.claude/commands/robot-test.md`
