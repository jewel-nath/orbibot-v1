# Bringup Issue Tracker

**Package:** `orbibot_bringup` (cross-package launch orchestration)
**Last Updated:** 2026-08-03

---

## 🔴 Open

### BRINGUP-1: Killing the bringup leaves an orphaned LiDAR launch running
**Opened:** 2026-08-03 · **Severity:** HIGH — "I stopped the robot" can be false
**File:** `launch/robot.launch.py` lines ~62–71

The LiDAR is started with `ExecuteProcess(cmd=['ros2', 'launch',
'orbibot_sensors', 'lidar.launch.py'])`, deliberately, to keep the two USB
serial devices isolated:

```python
# Lidar (delayed, launched as separate subprocess for isolation)
# Using ExecuteProcess instead of IncludeLaunchDescription to avoid
# USB serial conflict between /dev/motordriver and /dev/lidar
```

The isolation works. The lifecycle does not. That inner `ros2 launch` is a
**separate process group**, so when the outer bringup dies the inner one is
reparented to PID 1 and keeps running — and being a launch file, it *respawns*
`rplidar_composition` every time the node is killed.

Observed 2026-08-03:

```
kill <bringup>          → rplidar_composition 2412 still alive
kill 2412               → respawned as 3085
kill 3085               → respawned as 3174
ps -o ppid              → parent 2409 = "ros2 launch orbibot_sensors
                          lidar.launch.py", PPID 1, orphaned
kill 2409               → finally stops
```

**Why this is a safety issue, not a tidiness one.** The operator's mental model
after Ctrl+C is "the robot stack is stopped". It is not. A node is still holding
`/dev/lidar`, still spinning the LiDAR motor, and still publishing `/scan` —
which a later `ros2 launch` will silently fail to acquire the port for. The
`.claude/rules/robot-safety.md` instruction to "leave no node publishing" cannot
be satisfied by stopping the thing you started.

**How to resolve** (in preference order):

1. Use `IncludeLaunchDescription` and solve the serial conflict properly — the
   conflict was between *devices*, and udev already gives them stable distinct
   symlinks, so the original reason may no longer hold
2. If the subprocess must stay, add `on_exit=[EmitEvent(event=Shutdown())]` and
   start it in the same process group so a signal reaches both
3. At minimum, document the required teardown and add it to
   `.claude/scripts/preflight.sh` as a pre-run check for stale nodes

---

## See also

- `src/orbibot_hardware/hardware-issue.md` — HW-BUG-9, motors auto-enable at launch
- `docs/architecture/command-pipeline.md` — who is allowed to drive the robot
- `.claude/rules/robot-safety.md`
