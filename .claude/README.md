# .claude — Claude Code configuration

Everything here shapes how Claude Code works on OrbiBot. The split follows one
question: **does the agent need this every session, or only some sessions?**

```
.claude/
├── rules/       Always loaded. Behavioural constraints only — keep short.
├── hooks/       Fire regardless of what the agent remembers.
├── skills/      Loaded on demand. Reference material, procedures, templates.
├── scripts/     Run by hand or by the agent, on the real robot.
├── commands/    Slash commands. Load only when invoked.
└── settings.json
```

## rules/ — always loaded, so keep it small

| File | Constrains |
|---|---|
| `robot-safety.md` | **Physical safety** — BOOT0, robot state, how to stop it |
| `docs-sync.md` | Keep docs true after every change, deletions included |
| `code-style.md` | Naming in Python and C |
| `git-workflow.md` | Commit per logical unit, before moving on |

Four files, ~350 lines. Each name says *when it applies*. Anything longer than a
page of constraints does not belong here — if it is a procedure or a template,
it is a skill.

## hooks/ — the part that does not depend on memory

`SessionStart` records the repo's HEAD. `Stop` compares against it and
interrupts if the session changed code under `src/` but no documentation. It
fires at most once per distinct set of undocumented files, so it cannot loop and
cannot nag twice about the same edits.

A rule alone was not enough: a README-workflow rule already existed while
several documents drifted into being confidently wrong — including a firmware
changelog that recorded a misconfigured register as a hardware fact, and shipped
a compensation factor for it that survived four months. Rules carry the
judgment; the hook makes sure the question gets asked.

## skills/ — loaded only when used

25 skills, auto-discovered from their own frontmatter. A skill's body costs
nothing until Claude decides it is relevant, so depth is cheap here and breadth
is not: near-duplicate skills make that decision worse, not better.

Roughly: **ROS 2 mechanics** (`ros2_*`), **robot subsystems** (`microcontrollers`,
`serial_can_protocols`, `realtime_motor_control`, `control_systems`,
`robot_modeling`, `sensor_fusion_slam`, `nav2`, `lidar_pointcloud`,
`robot_perception`), **system-level** (`robot_bringup`, `robotics_design_patterns`,
`robotics_software_principles`, `safety_systems`, `robotics_testing`,
`ros2_web_integration`).

There is deliberately no hand-written index. The previous one listed every skill
by name and went stale in 20 places the moment seven were deleted.

Removed 2026-08-03, with the reason:

| Skill | Why |
|---|---|
| `docker_ros2_development` | No Docker anywhere in this repo |
| `robotics_security` | SROS2 / IEC 62443, aimed at fleets — this is one LAN robot |
| `camera_vision` | Covered by `robot_perception`; the RealSense is a webcam here |
| `path_planning` | This robot uses Nav2's planners, not custom ones |
| `robot_architecture` | Covered by `robotics_design_patterns` |
| `edge_ml_deployment` | TensorRT / Jetson; nothing in the roadmap needs it |
| `learning_robotics` | Imitation learning and RL; this is a classical stack |
| `gazebo`, `sim_to_real` | Simulation was dropped — see below |

`.claude/guides/` went at the same time: four generic walkthroughs, 1800 lines,
zero mentions of OrbiBot, and written for ROS 2 **Humble** in a Jazzy repo. The
matching skills cover the same ground and are discoverable.

## scripts/ — for the real robot

| Script | Does |
|---|---|
| `preflight.sh` | Run before operating: devices, nodes, battery |
| `safety.sh` | Cross-checks firmware limits against the ROS 2 config |
| `diag.sh` | Collects system status for troubleshooting |
| `encoder.sh` | Diagnoses encoder communication failures |
| `motor.sh` | Spins each wheel briefly — **wheels must be free** |

## No simulation

`orbibot_gazebo` was removed on 2026-08-03. Claude Code runs on the robot's own
Pi 5, which *is* the robot — a simulator sitting beside the real thing earns
nothing, and Gazebo pulled 202 MB of `gz` packages onto a machine with no GPU,
where the render engine a simulated LiDAR needs would fall back to software.

It is not lost: the commit that added it is still in history, so
`git checkout <sha> -- src/orbibot_gazebo` brings it back if the work ever moves
to a laptop.

## Where the project knowledge lives

Not here. `CLAUDE.md` at the repo root is the map. Documentation lives beside the
code it describes — `src/<pkg>/README.md`, `<pkg>-issue.md`, `<pkg>-changelog.md`.
Rules constrain *how* to work; those record *what is true* about the robot.
