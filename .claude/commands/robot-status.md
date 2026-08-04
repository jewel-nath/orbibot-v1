# /robot-status — is the robot healthy right now?

Read-only. Moves nothing, changes nothing. Safe for anyone to run at any time,
and the right first thing to run when you do not know what state things are in.

## Do this

1. **Is anything already running?**

   ```bash
   .claude/scripts/stop.sh --check
   ```

   Reports running nodes and whether `/dev/lidar` and `/dev/motordriver` are
   held. It changes nothing in `--check` mode.

2. **Is the hardware attached?**

   ```bash
   ls -l /dev/motordriver /dev/lidar
   for d in /sys/bus/usb/devices/*/; do
     [ -f "$d/product" ] && grep -qi realsense "$d/product" 2>/dev/null \
       && echo "RealSense — $(cat $d/speed) Mbps"
   done
   ```

   Both symlinks should exist. RealSense is expected to read **480 Mbps** today
   — that is SENS-2, a known open issue, not a new fault.

3. **If the stack is not running, start it** — `/robot-start` — then read the
   live numbers. If it is already running, go straight on.

4. **Battery and motor state:**

   ```bash
   ros2 topic echo /orbibot/system_status --once
   ```

5. **Topic rates** — the numbers that say whether the base is healthy:

   ```bash
   for t in /scan /odom /odometry/filtered /imu/data_raw /joint_states /cmd_vel; do
     echo -n "$t: "
     timeout 12 ros2 topic hz $t --window 40 2>&1 \
       | grep -oE 'average rate: [0-9.]+' | tail -1
   done
   ```

## What good looks like

Measured 2026-08-04, robot elevated, motors disabled. Compare against these,
and treat a difference as something to explain rather than ignore:

| Topic | Expected | Notes |
|---|---|---|
| `/scan` | **8.0 Hz** | the A1's motor speed. Not 10 — see SENS-1 |
| `/imu/data_raw` | **50.0 Hz** | |
| `/joint_states` | **50.0 Hz** | |
| `/odometry/filtered` | **50.0 Hz** | EKF, re-derived 2026-08-04 |
| `/odom` | **~2 Hz when still**, ~50 Hz moving | deduplicated + 0.5 s heartbeat. Not a bug |
| `/cmd_vel` | **20 Hz** | the idle source; publisher count must be **1** |
| `battery_voltage` | 12.8 V nominal | 11.0 warning, **10.5 cutoff** |
| `motors_enabled` | `false` unless you armed them | |

```bash
ros2 topic info /cmd_vel     # Publisher count MUST be 1 (twist_mux)
```

More than one publisher on `/cmd_vel` means the arbitration has been bypassed —
stop and read [[command-pipeline]] before driving.

## Report it as numbers

Give the operator the measured figures, not adjectives. If something is off
spec, say which number and by how much, then check whether it is already a known
issue before calling it new:

- `src/<pkg>/<pkg>-issue.md` — open findings per package
- [docs/moc/backlog-moc.md](../../docs/moc/backlog-moc.md) — the map of them all
- `src/orbibot_rosmaster_firmware/test-report.md` — what was verified live, when

## Related

`/robot-start` · `/robot-stop` · `/robot-drive` · `/robot-test`
