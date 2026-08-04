# /robot-fix — something is wrong, work out what

Triage first, hypothesis second. Most failures on this robot have looked like
something they were not, and the cost has always been the same: acting on the
first plausible story instead of the cheapest check.

---

## Rule zero

**Check whether it is already known before diagnosing it.**

```bash
grep -rn "<symptom keyword>" src/*/*-issue.md docs/reference/field-notes.md
```

- `src/<pkg>/<pkg>-issue.md` — open findings, per package
- [docs/moc/backlog-moc.md](../../docs/moc/backlog-moc.md) — the map of them all
- [docs/reference/field-notes.md](../../docs/reference/field-notes.md) — traps
  that already cost time

## Rule one

**Read the code that produces the number before deciding the number is wrong.**

`/odom` at 1.94 Hz next to `/joint_states` at 49.97 Hz — from the same serial
frames — was filed as an impossible bug. It is a deliberate heartbeat: unchanged
odometry is deduplicated and re-sent every 0.5 s. Nothing was broken.

Likewise a documented spec may be the datasheet **maximum**: `/scan` at 7.9 Hz
was filed as a 21 % shortfall against a "10 Hz" that the A1 never claimed.

---

## Symptom → first check

| Symptom | Check this first |
|---|---|
| **LiDAR `RESULT_OPERATION_TIMEOUT`** | `ros2 param get /rplidar_node serial_port` → must be `/dev/lidar`. Then `pgrep -cf '^/opt/ros/jazzy/lib/rplidar_ros/rplidar_composition'` → must be 0 or 1. **Neither occurrence of this was ever the LiDAR.** |
| **A node cannot open a serial port** | `.claude/scripts/stop.sh --check` — an orphan from a previous run is still holding it |
| **"I stopped it" but something is still publishing** | `stop.sh --check`. Killing a launch **without a controlling terminal** orphans all six nodes |
| **Board sends nothing** | A passive read returns 0 bytes on a *healthy* board — it only auto-reports when asked. Send the enable frame, or just run the hardware node |
| **Board dim LED, `ch341` re-enumerating** | Voltage. `journalctl -k \| grep ch341`. Power-cycle the board, measure the battery |
| **Commands do not reach the wheels** | `ros2 topic info /cmd_vel` — one publisher, and **type `Twist` on both ends**. A `TwistStamped` publisher and a `Twist` subscriber look connected and are not |
| **Robot does not stop when a source goes quiet** | Is `cmd_vel_idle` publishing? `ros2 topic hz /cmd_vel_idle` → 20 Hz. twist_mux emits nothing when every input is silent |
| **A rate is below spec** | Is it CPU? `top -bn2 \| grep '^%Cpu'`. This machine is usually 98 % idle, so it is almost never CPU |
| **A tuning value looks wrong** | [[inherited-values]] — it may be fitted to the Raspberry Pi and simply void |
| **Tests pass alone, fail together** | `sys.modules` pollution. Run the directory *and* a different order |
| **`dmesg` shows nothing wrong** | `dmesg` **reads nothing** on this machine. Use `journalctl -k` |

## Cheap checks before expensive ones

In this order, because each is faster than the one after and has caught real
faults here:

```bash
.claude/scripts/stop.sh --check          # orphans holding devices
ls -l /dev/motordriver /dev/lidar        # devices present
journalctl -k --since "-30min" | grep -iE 'ch341|cp210x|usb.*(new|disconnect)|under-volt'
ros2 topic info /cmd_vel                 # one publisher, matching types
ros2 topic echo /orbibot/system_status --once   # battery, motors_enabled
top -bn2 -d1 | grep '^%Cpu'              # is it actually load?
```

**Do not ask the operator for a physical action until the software checks are
done.** A USB replug was requested once for a fault that was twelve orphaned
processes; it cost a trip to the robot and proved nothing.

---

## When you have found it

1. **Fix the cause, not the reading.** A compensation factor once hid a
   misconfigured register for four months and made two axes worse while making
   the third look right. Roadmap Principle 3.
2. Record it in `src/<pkg>/<pkg>-issue.md` — what it was, how it was proved, and
   what the measurement was.
3. If the diagnosis overturns something already written down, **say so and
   correct the record**, including if it was your own earlier conclusion.
4. If it was non-obvious, add it to [[field-notes]]. The bar: *would you have
   saved an hour if you had read it this morning?*
5. Ask whether the fix made a document untrue — `.claude/rules/docs-sync.md`.
6. Commit with the reasoning, not just the change.

## Related

`/robot-status` · `/robot-test` · `/robot-stop` · [[field-notes]] ·
[[backlog-moc]] · `.claude/rules/docs-sync.md`
