# Bringup Issue Tracker

**Package:** `orbibot_bringup` (cross-package launch orchestration)
**Last Updated:** 2026-08-04

---

## ✅ Fixed

### BRINGUP-2: the LiDAR was opening `/dev/motordriver`
**Opened and fixed:** 2026-08-04 · **Severity:** HIGH — the LiDAR never started
**File:** `launch/robot.launch.py`

Included launch files share **one launch context**, and `DeclareLaunchArgument`
does not overwrite a value already in it. Two packages declare the same argument
name:

```
hardware.launch.py   'serial_port'  default /dev/motordriver
lidar.launch.py      'serial_port'  default /dev/lidar
```

Whichever is included first wins for both. `hardware.launch.py` is included
first, so `rplidar_composition` opened **`/dev/motordriver`**, sent RPLidar A1
commands to the ROSMaster board, got no reply, and died:

```
[rplidar_node] Error, operation time out. RESULT_OPERATION_TIMEOUT!
```

Verified directly rather than inferred:

```
$ ros2 param get /rplidar_node serial_port
String value is: /dev/motordriver          # before
String value is: /dev/lidar                # after
```

**This is what the old `ExecuteProcess` workaround was hiding.** Its comment
read *"to avoid USB serial conflict between /dev/motordriver and /dev/lidar"* —
the symptom was real, the explanation was not. There is no device conflict; the
two have separate udev symlinks and separate processes. A separate `ros2 launch`
subprocess simply gets a separate launch context, which sidestepped the
collision at the cost of an orphaning second launch service (BRINGUP-1).

**Fix.** `robot.launch.py` now declares `motor_port` and `lidar_port` under
distinct names and passes each include an explicit `launch_arguments`, so no
include inherits an ambient value. Adding a package later cannot silently
repoint a device.

**Watch for this pattern elsewhere.** Any two included launch files sharing an
argument name have it. Grep before adding an include:

```bash
grep -rhn "DeclareLaunchArgument" -A1 src/*/launch/*.py | grep -oP "^\s*'\K[a-z_]+(?=')" | sort | uniq -d
```

---

## 📝 Corrected

### BRINGUP-1: teardown — the original diagnosis was wrong
**Opened:** 2026-08-03 · **Re-measured:** 2026-08-04 · **Severity:** HIGH → MEDIUM

The original entry claimed *"Killing the bringup leaves an orphaned LiDAR launch
running"* and that *"'I stopped the robot' can be false"*. Measured properly,
the headline is false and the real condition is narrower.

**Ctrl+C in a real terminal stops everything, cleanly.** Measured with the launch
under a pseudo-terminal, so that writing `0x03` makes the kernel deliver SIGINT
to the foreground process group exactly as a keypress does:

| Controlling terminal | Stop method | Result |
|---|---|---|
| yes | **Ctrl+C** | **CLEAN — 1.1 s**, LiDAR included |
| yes | SIGTERM to launch pid | CLEAN — 0.5 s |
| yes | SIGINT to launch pid | CLEAN — 5.4 s |
| yes | SIGKILL to launch pid | CLEAN — 0.5 s (session leader dies → kernel SIGHUPs the group) |
| **no** | SIGTERM or SIGKILL | **all 6 nodes orphaned at PPID 1** |
| **no** | SIGINT to pid | nothing dies at all |
| **no** | SIGINT to process group | every node **respawned** during shutdown |

So the variable is the **controlling terminal**, not the LiDAR. And when it
fails it orphans *all six* nodes — `robot_state_publisher`, `hardware_node`,
`system_monitor`, `imu_filter_madgwick`, `ekf_node` and `rplidar_composition` —
not just the LiDAR. The LiDAR was merely the visible one, because a surviving
inner launch kept respawning it and the motor kept spinning.

**Why the original report saw it.** It was made from an agent session, where the
launch runs as a background job with no controlling terminal. That is a real
environment — it is also how a systemd unit or an `ssh host 'ros2 launch …'`
runs — but it is not how the operator drives the robot.

**Where it stands.** The nested launch layer is gone (BRINGUP-2), so there is one
launch service instead of two. For the headless case, `.claude/scripts/stop.sh`
stops the stack and then **verifies that `/dev/lidar` and `/dev/motordriver` are
released** — the check that actually matters, since a node still holding
`/dev/lidar` keeps the motor spinning and makes the next launch fail to open the
port.

`respawn=True` is set on every node in the base stack. It is what turns "killed"
into "resurrected" in the no-terminal case. Left as-is for now — it is real
resilience while the robot is running — but it is the reason `stop.sh` signals
launch processes before nodes.

---

## ⛔ Not a bug — closed the day it was opened

### BRINGUP-3: `/odom` publishes at 1.94 Hz
**Opened and closed:** 2026-08-04 · **Verdict:** working as designed

Measured on the full stack, robot elevated, motors disabled:

| Topic | Rate |
|---|---|
| `/joint_states` | 49.97 Hz |
| `/imu/data_raw` | 49.99 Hz |
| `/odometry/filtered` | 25.00 Hz |
| `/odom` | 1.94 Hz |

Opened on the reasoning that `/odom` and `/joint_states` come from the same
serial frames, so a 25× gap had to be a bug. That skipped reading the code.
`hardware_node._publish_firmware_odom()` **deduplicates unchanged odometry** and
re-sends it only as a heartbeat, `odometry.heartbeat_interval`, default 0.5 s.
A stationary robot produces identical odometry every frame, so 1/0.5 = 2 Hz is
the correct output.

Proved without needing motors, by changing the live parameter:

| `heartbeat_interval` | measured `/odom` |
|---|---|
| 0.5 s (default) | 1.948 Hz |
| 0.2 s | 4.659 Hz |
| 0.1 s | 8.474 Hz |

It tracks the interval. (Each is slightly under 1/interval because the check
runs on the 50 Hz sensor callback, so the wait rounds up to the next 20 ms
tick.) **`/odom` under motion is still unmeasured** — expect ~50 Hz once the
wheels turn, and confirm it during Phase 1.

**Lesson worth keeping:** a rate that looks wrong is not a bug until the code
that produces it has been read. This is the second time today the same mistake
appeared — see BRINGUP-1, where a claim was made from a test harness artifact
rather than the robot's real behaviour.

---

## See also

- `src/orbibot_hardware/hardware-issue.md` — HW-BUG-9 (motors auto-armed), fixed
- `src/orbibot_sensors/sensors-issue.md` — SENS-1 (`/scan` 7.9 Hz), SENS-2
- `docs/architecture/command-pipeline.md` — who is allowed to drive the robot
- `.claude/scripts/stop.sh` — headless teardown, with device-release verification
- `.claude/rules/robot-safety.md`
