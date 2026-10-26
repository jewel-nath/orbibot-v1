# .claude — Claude Code setup

How Claude Code is set up to work on OrbiBot: the rules it always follows, a
hook that keeps the docs honest, and scripts it can run on the robot. The
project's own documentation is not here: start at the root
[README](../README.md) and [CLAUDE.md](../CLAUDE.md).

```
.claude/
├── rules/       Always loaded. Behavioural constraints only — kept short.
├── hooks/       Fire regardless of what the agent remembers.
├── scripts/     Run by hand or by the agent, on the real robot.
├── commands/    Slash commands. Load only when invoked.
└── settings.json
```

## rules/ — always loaded, so kept small

| File | Constrains |
|---|---|
| `robot-safety.md` | **Physical safety**: BOOT0, the robot's state, how to stop it |
| `docs-sync.md` | Keep the docs true after every change, deletions included |
| `code-style.md` | Naming in Python and C |
| `git-workflow.md` | Commit per logical unit, before moving on |

## hooks/ — the part that does not depend on memory

`SessionStart` records the repo's HEAD. `Stop` compares against it and
interrupts if the session changed code under `src/` but no documentation. It
fires at most once per distinct set of undocumented files, so it cannot loop.

A rule alone was not enough: a documentation rule already existed while
several documents drifted into being confidently wrong, including a firmware
changelog that recorded a misconfigured register as a hardware fact, and
shipped a compensation factor for it that survived four months. The rule
carries the judgment; the hook makes sure the question gets asked.

## scripts/ — for the real robot

| Script | Does |
|---|---|
| `preflight.sh` | Run before operating: devices, nodes, battery |
| `safety.sh` | Cross-checks the firmware's limits against the ROS 2 config |
| `diag.sh` | Collects system status for troubleshooting |
| `encoder.sh` | Diagnoses encoder communication failures |
| `motor.sh` | Spins each wheel briefly: **the wheels must be off the ground** |

Known gaps, not fixed yet:

- `safety.sh` looks for keys that were renamed (`max_linear_velocity`,
  `battery_low_voltage`, `MOTOR_TIMEOUT`, `WATCHDOG_ENABLE`); the config now
  has `control.max_velocity`, `safety.battery_low_threshold`,
  `COMMAND_TIMEOUT_MS` and `WATCHDOG_TIMEOUT_MS`, so its cross-check finds
  nothing.
- `preflight.sh` reads `/orbibot/battery`, which nothing publishes; the
  voltage is on `/orbibot/system_status`.
- `encoder.sh` looks for a node called `/hardware_node`; it is
  `/orbibot_hardware_node`.
- `diag.sh` checks an `orbibot.service` systemd unit that the repo doesn't
  have.

## Skills

Earlier versions of this folder carried 25 generic robotics skills. They were
removed from this repository; a maintained, credited set lives in
[agentic-robotics](https://github.com/jewel-nath/agentic-robotics).

## No simulation

`orbibot_gazebo` was removed on 2026-08-03. V1 runs on its Raspberry Pi 5,
which has no GPU for a simulator. The package is still in the git history:
`git log --all -- src/orbibot_gazebo` finds it.
