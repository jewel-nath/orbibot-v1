# Hardware Node Issue Tracker

**Package:** `orbibot_hardware` (ROS 2 serial bridge, Python)
**Last Updated:** 2026-03-25

---

## 🔴 Open Bugs

### HW-BUG-9: `robot.launch.py` silently arms the motors 6 s after startup
**Opened:** 2026-08-03 · **Severity:** HIGH — safety
**File:** `launch/hardware.launch.py` lines ~30–67

```python
declare_start_enabled = DeclareLaunchArgument(
    'motors_enabled',
    default_value='true',          # <-- default
    description='Start with motors enabled'
)

motor_enable_cmd = TimerAction(
    period=6.0,
    actions=[ExecuteProcess(
        cmd=['ros2', 'service', 'call', '/orbibot/set_motor_enable',
             'orbibot_msgs/srv/SetMotorEnable', '{enable: true}'],
        name='motor_enable_startup',
        condition=IfCondition(motors_enabled))])
```

`hardware_node.py` itself never enables motors — it only exposes the service.
Reading the node alone therefore gives the wrong answer, and did: on 2026-08-03
the node was inspected, judged safe, and the stack launched on that basis. Six
seconds later the log read `[hardware_node-2] Motors enabled`.

**Consequence.** `ros2 launch orbibot_bringup robot.launch.py` — the documented
way to start the robot, in `CLAUDE.md` and the roadmap's Phase 0 gate — arms
four motors on a robot that may be sitting on the floor, with no prompt and no
mention in any doc. Nothing then commands motion, and the firmware's 2 s command
timeout is a genuine backstop, so the robot does not move. But "armed and
waiting for a command" is not the state the operator is told they are in.

**How to resolve:**

1. Flip `default_value` to `'false'`. Enabling motors should be an explicit act
   — `motors_enabled:=true`, or the dashboard's own control
2. If the default stays `true`, it must be stated in `CLAUDE.md`, the bringup
   README and `.claude/rules/robot-safety.md`, because all three currently imply
   the opposite
3. Log it at WARN, not INFO — it is the single most consequential thing the
   launch does

**Related:** `src/orbibot_bringup/bringup-issue.md` BRINGUP-1 — stopping the
stack does not reliably stop everything either.

---

### HW-BUG-8: `/imu/data_raw` runs at 40–45 Hz, not the documented 50 Hz
**Opened:** 2026-08-03 · **Severity:** MEDIUM
**Files:** `hardware_node.py`; firmware `task_communication.c`

Measured on the Beelink, `robot.launch.py` up, robot elevated, motors disabled:

```
ros2 topic hz /imu/data_raw  →  average rate 40.391, then 45.098
```

Documented as 50 Hz in the README, `system-overview` and the firmware README.
Actual is **10–20 % low, and visibly jittery** — the two windows differ by 4.7 Hz.

**Not CPU contention.** The machine was 98.6 % idle. `test-report.md` §9.5
recorded 52.5 Hz for the raw IMU on the Pi, so the rate has *dropped* while the
host got faster, which points at the serial link or the firmware's report
interleaving rather than the ROS 2 side.

The firmware interleaves five report types 1 ms apart on a 115200 baud link
(`task_communication.c`). That link is the one architectural bottleneck this
project has, and 5 × 50 Hz of packets is close to its limit — see
`improve-plan.md`.

**Why it matters:** Madgwick is configured `frequency: 50.0` and uses dt from
message headers. Phase 4 tunes `gain` and `zeta` against that. A filter told it
runs at 50 Hz while fed 43 Hz with jitter will be tuned wrong, and the error
will be blamed on the gains.

**How to resolve:**
1. Measure the actual serial throughput and packet loss at 115200
2. Compare against `test-report.md` §9.5's 52.5 Hz — what changed since?
3. Either raise the rate, or **correct every doc that claims 50 Hz**

---

### HW-BUG-1: EKF Output Rate ~2.5 Hz Instead of Configured 25 Hz
**Opened:** 2026-03-25 · **NOT REPRODUCIBLE on the Beelink, 2026-08-03**
**Severity:** ~~MEDIUM~~ — see the resolution note below

> **Measured 2026-08-03 on the Beelink SER5 Pro:** `/odometry/filtered` runs at
> **24.0–24.5 Hz** against a configured 25.0 — within 4 %. Robot elevated,
> motors disabled, full `robot.launch.py` stack up, whole machine at 1.3 % CPU.
>
> None of the three hypotheses below was tested and confirmed; the symptom
> simply does not occur on this hardware. The most likely explanation is that
> the Pi 5 could not sustain the EKF's timer under the full stack — it is the
> one variable that changed. **Do not close this by declaring a root cause that
> was never demonstrated.** If it reappears, the QoS and DDS hypotheses are
> still unexamined.
**Affects:** `orbibot_localization` (robot_localization EKF), navigation performance

**Symptom:** `/odometry/filtered` publishes at ~2.5 Hz regardless of robot state
(stationary or moving). The EKF `frequency` parameter is set to 25.0 Hz in
`ekf_params.yaml`, but actual output rate is 10x lower.

**Impact:** Nav2 controller (10 Hz) needs faster odometry for smooth trajectory tracking.

**Potential causes:**
1. QoS BEST_EFFORT subscriber dropping from RELIABLE publisher
2. robot_localization Jazzy version timer bug
3. DDS middleware (CycloneDDS) transport issue

**Workarounds to try:**
- `odom0_nodelay: true` / `imu0_nodelay: true` in EKF config
- Test with FastDDS instead of CycloneDDS

---

## 🟡 Technical Debt

### HW-TD-1: rosmaster_driver.py uses print() instead of logging
**Severity:** LOW
**File:** `rosmaster_driver.py`

Error handling in serial methods uses `print()` which doesn't appear in ROS 2 logs.
Should use a Python `logging.Logger` instance or accept a callback for the hardware_node
to route through `self.get_logger()`.

---

### HW-TD-2: Circular buffer in USART ISR is populated but never read
**Severity:** LOW
**File:** firmware `hal_usart.c` (cross-reference: FW-ISSUE-1)

The firmware USART ISR stores every byte in both the protocol state machine AND a 256-byte
circular buffer. The read functions (`hal_usart_available`, `hal_usart_read_byte`) are never
called. This wastes 256 bytes RAM and ISR cycles.

---

## 💡 Improvement Ideas

### Performance
- **Batch serial writes:** Group PID + motion commands into single serial write when
  both arrive in the same cycle, reducing USB round-trips.

### Reliability
- **Serial health metric:** Expose firmware `g_rx_drop_count` and `g_unknown_cmd_count`
  as ROS diagnostics for monitoring protocol errors.
- **Watchdog topic:** Publish a heartbeat from the driver thread so hardware_node can
  detect thread death (not just serial disconnect).

### Extensibility
- **Plugin-based sensor abstraction:** If more sensor boards are added in the future,
  the serial protocol parsing could be abstracted behind a plugin interface.

---

## ✅ Closed

*(See hardware-changelog.md for resolved bugs and improvements)*
