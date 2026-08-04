# /robot-stop — stop the robot, and prove that it stopped

## Do this

```bash
.claude/scripts/stop.sh
```

It escalates SIGINT → SIGTERM → SIGKILL, launch processes before nodes so
nothing gets respawned mid-teardown, then **verifies `/dev/lidar` and
`/dev/motordriver` were released** and exits non-zero if they were not.

To look without changing anything: `.claude/scripts/stop.sh --check`

## If motors are armed, disarm them too

```bash
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: false}"
```

Do this **before** killing the stack while the service still exists. If the
stack is already gone, the firmware's 2 s command timeout has stopped the
motors anyway, and they disarm on the next launch because `motors_enabled`
defaults to false.

## Emergency, right now

Fastest first:

1. **Ctrl+C** in the terminal running the launch — measured **1.1 s** to a full
   clean stop, LiDAR included
2. **Cut power at the battery**
3. From another terminal, override every command source:
   ```bash
   ros2 topic pub -r 20 /cmd_vel_estop geometry_msgs/msg/Twist \
     '{linear: {x: 0.0, y: 0.0}, angular: {z: 0.0}}'
   ```
   Priority 255 — beats the dashboard, the agent and Nav2 while it keeps
   publishing.

## Why the script exists when Ctrl+C works

Ctrl+C works **when the launch has a controlling terminal**. Measured
2026-08-04:

| Controlling terminal | Result |
|---|---|
| yes — a real terminal | clean, every path, 0.5–5.4 s |
| **no** — script, systemd unit, `ssh host '…'`, agent session | **all 6 nodes orphaned at PPID 1** |

Orphans keep publishing, keep holding the serial ports, and make the next launch
fail to open them. They are also invisible unless you look. `stop.sh` is the
answer for that case — and it is the one to use from any automation.

Full measurements: `src/orbibot_bringup/bringup-issue.md`, BRINGUP-1.

## Confirm

```bash
.claude/scripts/stop.sh --check     # expect "Nothing running" + devices free
ros2 node list                      # expect empty
```

## Related

`/robot-status` · `/robot-start` · `.claude/rules/robot-safety.md`
