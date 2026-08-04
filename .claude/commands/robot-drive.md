# /robot-drive — move the robot, safely, from a standing start

For someone who has just SSH'd in and wants the robot to move. Assume they have
never used ROS 2. **You are responsible for the safety gates, not them.**

Read `.claude/rules/robot-safety.md` before the first command of this session.

---

## The rule you cannot skip

**Never assume a physical action happened. Ask for one thing, then wait.**

The operator is next to the robot and will do anything you ask — but only if you
ask clearly, one action at a time, and then stop talking and wait for them to
confirm. Do not batch requests. Do not carry a state assumption across turns: if
the robot was on a stool an hour ago, ask again.

---

## Step 1 — decide which state the test needs, and say why

| State | Valid for | **Not** valid for |
|---|---|---|
| **Elevated** — on a stool, wheels free | direction, sign, PID step response, protocol | anything measuring distance, drift or traction |
| **On the ground**, ≥ 2 m clear | odometry, drift, traction, mapping, navigation | — |

Tell the operator which one you need and why, then ask:

> **রোবট নিচে নামান, চারপাশে ~২ মিটার ফাঁকা রাখুন** — হয়ে গেলে বলুন।

or

> **রোবট stool-এর উপর তুলুন, চাকা ফাঁকা রাখুন** — হয়ে গেলে বলুন।

**Then wait.** Do not proceed on silence.

## Step 2 — say how to stop it, before anything moves

Tell them, every time, in plain words:

- **Ctrl+C** in the terminal running the launch — measured to stop the whole
  stack in **1.1 s**
- Or **cut power at the battery**
- Or from another terminal: `.claude/scripts/stop.sh`

## Step 3 — check the state you are actually in

```bash
.claude/scripts/preflight.sh
ros2 topic info /cmd_vel          # Publisher count MUST be 1 (twist_mux)
ros2 topic echo /orbibot/system_status --once | grep -E 'battery|motors_enabled'
```

Battery below **11.0 V**: say so and ask before continuing. Below **10.5 V**:
stop, that is the cutoff.

If `/cmd_vel` has more than one publisher, the arbitration is bypassed — do not
drive. See [[command-pipeline]].

## Step 4 — start the stack, motors disarmed

```bash
ros2 launch orbibot_bringup robot.launch.py
```

`motors_enabled` defaults to **false** on purpose. Launching does not arm
anything.

## Step 5 — arm, deliberately

```bash
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"
```

Say out loud that the motors are now live.

## Step 6 — drive

Publish to **`/cmd_vel_web`**, never `/cmd_vel`. `twist_mux` owns `/cmd_vel`;
publishing there directly bypasses the e-stop and every timeout.

```bash
# forward, gently — 0.15 m/s is enough to measure almost anything
ros2 topic pub -r 20 /cmd_vel_web geometry_msgs/msg/Twist \
  '{linear: {x: 0.15, y: 0.0}, angular: {z: 0.0}}'
```

Mecanum, so all three axes work: `linear.x` forward, `linear.y` **strafe**,
`angular.z` turn.

Keep bursts to **seconds, not minutes**. Ctrl+C on that publish command stops it
— the robot stops within 300 ms because the source went silent.

**Emergency stop** from any terminal, overrides everything:

```bash
ros2 topic pub -r 20 /cmd_vel_estop geometry_msgs/msg/Twist \
  '{linear: {x: 0.0, y: 0.0}, angular: {z: 0.0}}'
```

## Step 7 — disarm, every time

```bash
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: false}"
.claude/scripts/stop.sh
```

Leave nothing publishing `cmd_vel`. `stop.sh` verifies the serial devices were
released.

---

## Limits already enforced for you

Defence in depth. You should still keep commands gentle, but these exist:

| Layer | Behaviour |
|---|---|
| `twist_mux` | source goes silent → stop in **291 ms** (measured) |
| driver `cmd_timeout` | 2.0 s without a command → stop |
| firmware `COMMAND_TIMEOUT_MS` | 2.0 s → stop. Verified live, `test-report.md` §7.1 |
| firmware battery lockout | below 10.5 V → motors cut |
| firmware velocity clamp | 1023 mm/s peak on a 3000 mm/s command |

## Write down what happened

If you measured anything — distance, drift, current, a rate — it goes into
`src/orbibot_rosmaster_firmware/test-report.md` with the **date and the robot's
state**, or into the package's `<pkg>-issue.md`. A number left in the terminal
gets re-measured next month.

## Related

`/robot-status` · `/robot-stop` · `/robot-test` · [[command-pipeline]] ·
`.claude/rules/robot-safety.md`
