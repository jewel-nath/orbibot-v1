# /robot-test — test something, and record what it said

Start at [docs/operations/test-index.md](../../docs/operations/test-index.md).
It lists every test, what to run, when it was last run and what it returned.
**Read the "last run" column before running anything** — the answer may already
exist, and if it does, the interesting question is whether it still holds.

---

## Pick by what the test needs

| Needs | Then |
|---|---|
| Nothing | run it now |
| The board, no motion | check nothing else is running first |
| **Robot elevated** | ask the operator, **then wait** |
| **Robot on the ground, 2 m clear** | ask the operator, **then wait** |

Never carry a robot-state assumption across turns. If it was on a stool an hour
ago, ask again. `.claude/rules/robot-safety.md`.

## The quick ones, in order

```bash
# 1. Host-side unit tests — no robot at all
python3 -m pytest src/orbibot_hardware/tests/ -q

# 2. Build
source /opt/ros/jazzy/setup.bash && colcon build --symlink-install

# 3. Nothing already running?
.claude/scripts/stop.sh --check

# 4. Stack health — rates, battery, arbitration
#    (start the stack first if it is not up: /robot-start)
/robot-status

# 5. Command arbitration — priorities, timeouts, e-stop. No motion.
python3 .claude/scripts/test_cmd_vel_arbitration.py
```

**Run the unit tests as a directory, not file by file.** This suite passed
per-file while 35 tests failed in a directory run, because one file stubs
`rclpy` in `sys.modules` and never restores it. Per-file green is not green.

## Firmware suite

Serial only, no ROS needed. Robot **elevated** — some of these spin motors.

```bash
cd src/orbibot_rosmaster_firmware/tests
python3 run_all_tests.py --port /dev/motordriver     # all 17
python3 test_kinematics.py --port /dev/motordriver   # one
```

Ask for the robot to be elevated before running the suite, and wait.

---

## Then write down what it said

**This is the part that gets skipped, and it is the point of the exercise.**
A number that stays in the terminal is a number somebody re-measures next month.

| What you got | Where it goes |
|---|---|
| A number measured on hardware | `test-report.md`, dated section |
| A new finding, or one fixed or worsened | `src/<pkg>/<pkg>-issue.md` |
| A rate or CPU figure | [[baseline-results]] |
| Something non-obvious you learned | [[field-notes]] |
| **Always** | the "last run" column in [[test-index]] |

Record the **conditions** with the number: robot elevated or on the ground,
which firmware, how many samples, battery on charge or not. A power test run
with the charger still connected has already had to be thrown away once.

## Reporting

Numbers, not adjectives. *"|a| = 9.971, ratio 1.017"*, not *"IMU looks fine"*.

If a test fails, say so plainly with the output. Never round a failure up to a
pass. If a result contradicts an earlier conclusion — including one of your own
— say that directly and correct the record; that has already happened on this
robot and cost real time.

## Before calling something a bug

Check it is not already known, and not a misreading:

- `src/<pkg>/<pkg>-issue.md`, and [[backlog-moc]] for the map
- [[field-notes]] — several "obvious bugs" here were the code working as designed
- **Read the code that produces the number before calling the number wrong.**
  `/odom` at 1.94 Hz looked impossible next to `/joint_states` at 50 Hz; it was
  a deliberate heartbeat.

## Related

`/robot-status` · `/robot-drive` · `/robot-check` · `/robot-fix` · [[test-index]] ·
[[testing-guide]] · `.claude/rules/robot-safety.md`
