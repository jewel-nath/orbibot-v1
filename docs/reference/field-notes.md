---
title: "Field Notes"
type: reference
tags:
  - reference
  - debugging
  - traps
---

# Field notes — things that were not obvious

Hard-won knowledge about **this** robot and **this** machine: traps that cost
real time, measurements that overturned an assumption, and tools that lie.

This file is append-only in spirit. Every entry earned its place by being
believed wrongly at least once.

**When you learn something here, write it here.** Not in a commit message, not
in a conversation — those are gone by next month, and nobody greps history
before debugging. The discipline is in `.claude/rules/docs-sync.md`; the bar is
*would you have saved an hour if you had read it this morning?*

---

## Tools that lie on this machine

### `dmesg` reads nothing, and `grep -c` reports 0 anyway

`kernel.dmesg_restrict` is set. An unprivileged `dmesg` fails with *"read kernel
buffer failed: Operation not permitted"*, so `dmesg | grep -c pattern` returns a
confident **0** having read no log at all.

**Use `journalctl -k`.** Works for any user in the `adm` group.

Cost: a power-test conclusion ("zero resets") that was verified by a command
which read nothing. `test-report.md` §9.6.

### `pgrep -f` matches the shell that mentions the pattern

`pgrep -f 'rplidar_composition'` matches your own `bash -c '… rplidar_composition …'`
wrapper. `pkill -f` on that pattern then kills the shell running the pkill,
half-way through, leaving the real cleanup undone.

Filter by `argv[0]` before killing:

```bash
for p in $(pgrep -f "$PATTERN"); do
  a0=$(tr '\0' '\n' < /proc/$p/cmdline | head -1)
  case "${a0##*/}" in bash|sh|dash) continue;; esac
  kill "$p"
done
```

`.claude/scripts/stop.sh` does this. Cost: one truncated cleanup that left six
orphaned nodes.

**This has now cost three separate sessions**, and the third one was not a
`pkill` at all — it was a `/proc` scan written *to avoid* `pgrep`, which then
made the same mistake by matching the full command line. It reported the `bash`
wrapper as `hardware_node` and measured it at **0.0 % CPU**, which reads exactly
like "the node is idle" rather than "you are measuring the wrong process".

Whenever you match a process by name, **match `argv[0]`, not the command line** —
and treat a suspiciously clean `0.0 %` as a sign you found a shell.
`.claude/scripts/topic_rate_log.py` has the Python version of the filter.

### ROS `setup.bash` cannot be sourced under `set -u`

It reads unset variables and aborts the script with `AMENT_TRACE_SETUP_FILES:
unbound variable` or `COLCON_TRACE: unbound variable`. Wrap it:

```bash
set +u
source /opt/ros/jazzy/setup.bash
source install/setup.bash
set -u
```

Cost: a build stage that exited 0 having built nothing.

---

## Failures that were not what they looked like

### `RESULT_OPERATION_TIMEOUT` from the LiDAR — usually not the LiDAR

Twice on 2026-08-04, and neither was hardware:

1. The node had been handed **`/dev/motordriver`** and was sending A1 commands
   to the motor board (BRINGUP-2)
2. **Twelve** `rplidar_composition` processes were contending for `/dev/lidar`

The second survived a USB replug, which made it look even more like hardware and
cost the operator a wasted trip to the robot.

```bash
ros2 param get /rplidar_node serial_port      # must be /dev/lidar
pgrep -cf '^/opt/ros/jazzy/lib/rplidar_ros/rplidar_composition'   # must be 0 or 1
```

A genuinely wedged A1 still answers S/N, `Firmware Ver` and `Hardware Rev`, and
fails only at the health check and scan start. If identity queries fail too,
suspect power or cabling.

### The ROSMaster board is silent unless asked

A passive `serial.read()` on `/dev/motordriver` returns 0 bytes on a perfectly
healthy board — it only auto-reports after the driver enables it. "Zero bytes"
is **not** evidence the board is dead.

Send the enable frame first, then listen:

```python
body = bytes([0xFF, 0xFC, 0x04, 0x01, 0x01])
s.write(body + bytes([sum(body[2:]) & 0xFF]))
```

Cost: an incorrect "the board is unpowered" diagnosis.

### A dim power LED and repeated `ch341` re-enumeration means voltage

Board LED dim, `ch341-uart ttyUSB0: converter now disconnected` twice in 13 s,
MCU not transmitting: the board is browning out or its supply is broken. A power
cycle fixed it 2026-08-04. If it recurs, check `journalctl -k` for `ch341`
before touching the ROS side.

---

## Reasoning traps

### Reading the node is not reading the launch

`hardware_node.py` never enables motors. `hardware.launch.py` did, on a 6 s
timer, with `motors_enabled` defaulting to `true`. The node was read, judged
safe, and the stack launched on that basis — six seconds later the log read
`Motors enabled`.

**Open both.** HW-BUG-9.

### A rate that looks wrong is not a bug until you read the code that makes it

`/odom` at 1.94 Hz next to `/joint_states` at 49.97 Hz, from the same serial
frames, looked impossible. It is deliberate: unchanged odometry is deduplicated
and re-sent only as a heartbeat every 0.5 s. A stationary robot produces
identical odometry every frame.

Proved by moving the live parameter — 0.5 s → 1.948 Hz, 0.2 s → 4.659 Hz,
0.1 s → 8.474 Hz. BRINGUP-3.

### Documented specs may be the datasheet maximum

`/scan` measured 7.9 Hz against a documented 10 Hz and was filed as a 21 %
shortfall. The A1's actual spec is *"5.5 Hz, configurable up to 10"*. Twelve
documents had quoted the ceiling as the rate. 8.0 Hz was correct all along, and
the fix was to the documentation. SENS-1.

### Measuring with the charger connected measures the charger

The P-3 battery-sag test was run once with the charger still plugged in. The
numbers were void. The operator caught it, not the process.

### Do not write the measurement before measuring

A config comment was written claiming "49.98 Hz, 3.6 % of one core" before the
measurement ran. Actual: 49.999 Hz, 1.6 %. Nobody would have checked. Write the
value after you have it.

---

## Testing traps

### A test suite that passes per-file can still be broken

`sys.modules` is process-global and pytest imports every test module during
collection, before running anything. One file stubbing `rclpy` or a driver
module poisons every later file that wants the real thing — and the stub is
already in place before any fixture can run.

Measured in `orbibot_hardware/tests` on 2026-08-04:

| how it was run | result |
|---|---|
| each file on its own | 81 passed, 1 failed |
| the directory | **46 passed, 35 failed** |

Nothing was wrong with the code under test. **Always run the whole directory,
and run it in more than one order**, or the suite is only testing that files
work in isolation.

Fixed by evicting stubs before importing the real module, and a
`real_ros_modules` fixture in `conftest.py` for tests that need genuine ROS.

---

### A table maintained in three places will disagree, and each copy looks fine

The serial protocol table lives in `protocol.h`, `rosmaster_driver.py` and the
test harness. Two said `0x09 = FUNC_RESET_ODOM`; the harness said `SET_MOTOR`.
Each file was internally consistent, so nothing was obviously broken — and the
firmware has no per-motor command at all, so `SET_MOTOR` was pure fiction.

The test that used it asked a human *"Did the wheel spin FORWARD?"* about a
wheel that was never commanded. **An interactive test can report a pass for
something that physically did not happen.**

Diff duplicated tables mechanically rather than by eye, and prefer a test that
asserts agreement over a refactor that merges them — merging C built by
PlatformIO with Python installed by colcon trades a naming problem for a
build-system one. `test_protocol_table_agreement.py`.

### "Nothing changed but elapsed time" is a claim, and it is usually false

HW-BUG-8 was characterised three times in one day and the first two were wrong.

It was closed on four `/imu/data_raw` windows reading 49.99 Hz — spread
0.012 Hz, thoroughly convincing. Two and a half hours later the same stack read
39–44 Hz, so it was reopened as *"decays with board uptime"*, on the reasoning
that **nothing had changed but elapsed time**.

Something had. A node added that afternoon, `cmd_vel_idle`, publishes zeros on
`/cmd_vel` at 20 Hz forever — and 20 Hz of `/cmd_vel` costs the hardware node a
third of its publish rate. The two measurements straddled that commit. Elapsed
time was a coincidence lying on top of a regression, and it was persuasive
precisely because it came with a tidy monotonic story.

Two habits, both cheap:

- When you catch yourself writing *"nothing changed but X"*, run `git log
  --since` over the interval before believing it. Your own commits are the
  changes you are least likely to suspect.
- Before closing an intermittent fault, ask **what interval does it vary on**
  and sample across that interval. If the answer is unknown, the honest status
  is "not observed today", not "not reproducible".

### Measure the layer below before designing an experiment on top of it

The plan that followed from *"decays with board uptime"* was: power-cycle the
board, then measure every 15 minutes for three hours. It required the operator
to keep the robot powered all evening, and it would have measured nothing.

What actually settled it was **fifteen seconds** spent one layer lower — reading
the ROSMaster's serial stream directly with no ROS stack running. It reported
49.98 Hz at 2 h 41 min of board uptime, while ROS had reported 39.0 Hz nine
minutes *earlier* at a shorter uptime. The firmware was innocent, so the
variable named in the hypothesis could not exist, and the three-hour experiment
died before it was run.

A layered system gives this for free: firmware, serial, driver, topic. When a
number is wrong at the top, measure the bottom first — it is almost always the
cheapest measurement available and it eliminates whole strata at once.

`.claude/scripts/rate_decay_log.py` (serial layer) and `topic_rate_log.py` (ROS
layer) exist so this comparison stays a two-command job.

### Bisect by launching one thing at a time

Once the firmware was cleared, the cause took four 40-second runs: the hardware
node alone (50.0 Hz), plus localization (50.0), plus lidar (50.0), plus
twist_mux (37.4). Then one more run replaced twist_mux with a bare
`ros2 topic pub -r 20 /cmd_vel` and still reproduced it — which is what proved
twist_mux was a bystander rather than the culprit.

Launch files make this nearly free on this robot, and the last step matters
most: after a bisect fingers a component, **reproduce it without that
component**. Otherwise the fix goes into the wrong package.

### Prove a guard fails before trusting it

A test that has never failed is not evidence of anything. After writing the
agreement test, the original bug was reintroduced to confirm it was caught — it
failed three ways and named the byte. Do that every time; the alternative is a
regex that silently matches nothing and passes everything.

---

## Environment facts worth knowing

### Included launch files share one context

`DeclareLaunchArgument` does **not** overwrite a value already in the context, so
two packages declaring `serial_port` means whichever is included first wins for
both. Pass `launch_arguments=` explicitly to every include.

```bash
# find collisions before adding an include
grep -rhA1 "DeclareLaunchArgument" src/*/launch/*.py \
  | grep -oP "^\s*'\K[a-z_]+(?=')" | sort | uniq -d
```

BRINGUP-2.

### twist_mux on Jazzy defaults to TwistStamped

`use_stamped` defaults to **true**, and DDS does not connect a `TwistStamped`
publisher to a `Twist` subscriber. `ros2 topic info /cmd_vel` still reports one
publisher and one subscriber — looking correct — while nothing arrives. Pin
`use_stamped: false`.

### twist_mux publishes nothing when every input is silent

It is event driven. With all inputs quiet it emits **zero** messages, so the last
commanded velocity remains the newest message on the topic and nothing commands
a stop. Measured: 0 messages in the 3 s after the last input.

Fixed with a lowest-priority `cmd_vel_idle` source publishing zeros at 20 Hz, so
the mux always has something to fall through to. Stop latency 291 ms.

### Teardown depends on having a controlling terminal

| Controlling terminal | Result |
|---|---|
| yes | clean on Ctrl+C, SIGTERM, SIGINT **and** SIGKILL |
| **no** — script, systemd, `ssh host '…'`, agent session | **all 6 nodes orphaned at PPID 1** |

`SIGKILL` is clean *with* a terminal only because killing the session leader
makes the kernel `SIGHUP` the foreground group. Without one, use
`.claude/scripts/stop.sh`.

### Testing a launch from an agent session is not testing Ctrl+C

A background job has no controlling terminal, so `kill -INT` on it behaves
nothing like a keypress. To test the real thing, give it a pty (`os.forkpty()`)
and write `0x03`. Doing this overturned BRINGUP-1's entire diagnosis.

---

## Related

`.claude/rules/docs-sync.md` · [[roadmap]] · [[backlog-moc]] ·
[[test-index]] · `src/orbibot_rosmaster_firmware/test-report.md`
