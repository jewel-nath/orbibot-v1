# Hardware Node Issue Tracker

**Package:** `orbibot_hardware` (ROS 2 serial bridge, Python)
**Last Updated:** 2026-08-04

---

## 🔴 Open

*HW-BUG-8 is **reopened** — see below; closing it this morning was wrong.
HW-BUG-9 is fixed and HW-BUG-1 does not reproduce.*

### HW-BUG-9: `robot.launch.py` silently arms the motors 6 s after startup
**Opened:** 2026-08-03 · **FIXED 2026-08-03** · **Severity:** HIGH — safety
**File:** `launch/hardware.launch.py`

> **Fixed.** `motors_enabled` now defaults to `'false'`, the `TimerAction`
> itself carries the `IfCondition`, and arming logs a WARN-level line naming the
> argument that caused it. Verified by launching the stack and confirming
> `motors_enabled: false` in `/orbibot/system_status` with no `Motors enabled`
> line in the log — re-confirmed 2026-08-04.
>
> The original report is kept below because *how* it was missed is the useful
> part: the node was read, the launch was not.

**The code as it was:**

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

**How it was resolved:** `default_value` flipped to `'false'` (1), and the
arming path now logs at WARN naming the argument responsible (3). Point 2 did
not apply once the default changed.

**Related:** `src/orbibot_bringup/bringup-issue.md` — BRINGUP-2 (the LiDAR was
opening `/dev/motordriver`) and BRINGUP-1, whose original claim about teardown
turned out to be wrong; see the corrected measurements there.

---

### HW-BUG-8: serial-derived topics decay from 50 Hz with board uptime
**Opened:** 2026-08-03 · **Closed wrongly, then REOPENED 2026-08-04**
**Severity:** MEDIUM — Madgwick and the EKF are fed by this
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

> ### First re-measurement, 2026-08-04 ~14:45 — looked fine, and this conclusion was wrong
>
> Same conditions as the original: full `robot.launch.py`, robot elevated,
> motors disabled, machine 98.8 % idle. Four consecutive 50-sample windows:
>
> | window | `/imu/data_raw` |
> |---|---|
> | 1 | 49.998 Hz |
> | 2 | 49.992 Hz |
> | 3 | 50.004 Hz |
> | 4 | 49.998 Hz |
>
> Spread **0.012 Hz**, against the 4.7 Hz swing that defined the original
> report. `/joint_states` measured 49.967 and 50.003 Hz alongside. The rate is
> at spec and the jitter is gone.
>
> **The cause was never found, and is not being invented now.** The serial
> saturation hypothesis above was never tested — it remains plausible and
> unproven, and it does not explain why the symptom vanished.
>
> One intervening event is worth recording, as a lead rather than a conclusion:
> on 2026-08-04 the ROSMaster board entered a state where it **stopped
> responding entirely** — no serial data, dim power LED, `ch341` re-enumerating
> twice in 13 s — and the operator power-cycled it. The 40–45 Hz reading of
> 2026-08-03 may have been that same degradation partway along. Unproven.
>
> **If it returns, measure the board's behaviour before touching the ROS side**
> — check for `ch341` disconnects in `journalctl -k` first.

### REOPENED — 2026-08-04 17:09. It came back, and now it has a shape.

Same day, same stack, nothing changed but elapsed time:

| when | since board power-on | `/imu/data_raw` |
|---|---|---|
| 2026-08-03 | hours | 40.4, 45.1 Hz |
| 2026-08-04 **14:45** | **~10 min** | 49.998, 49.992, 50.004, 49.998 |
| 2026-08-04 **17:09** | **~2 h 32 min** | 44.6, 39.95, 41.0, 39.0 |

**The closure above was wrong.** Four windows inside ten minutes of a board
power cycle is not evidence a fault is gone — it is evidence of what a freshly
powered board does. An intermittent fault needs a measurement spread over the
interval it varies on.

**What the fault actually is, as far as measured:**

- **Both serial-derived topics decay together.** `/joint_states` measured
  40.6 Hz alongside `/imu/data_raw` 39.0 Hz. They share one 115200 link.
- **`/scan` is unaffected** — 8.087 Hz, normal. Different USB device, different
  driver. So this is the ROSMaster serial path, not the host or USB generally.
- **Not CPU.** Machine 95.7 % idle; `twist_mux`, `cmd_vel_idle` and
  `cmd_vel_source` each at 0.0 %.
- **No errors.** Zero `ch341` events in `journalctl -k`, no hardware_node
  timeouts or serial errors. The link is not failing, it is *slowing*.
- **A power cycle restores it**, which is how the 14:45 numbers were obtained.

**Leading hypothesis, untested:** something in the firmware's report scheduling
drifts with uptime — the five report types are interleaved 1 ms apart on a link
close to its limit (`task_communication.c`). A counter, timer or buffer that
degrades over hours would produce exactly this. **This is a hypothesis. Do not
write it down as the cause until it is measured.**

**How to resolve:**
1. **Characterise the curve.** Power-cycle the board, then measure
   `/imu/data_raw` every 15 min for 3 h. Is the decay linear, or a step?
2. Measure at the serial layer, below ROS — `tests/test_data_rate.py` — to
   separate firmware scheduling from the driver's read loop
3. Check whether traffic *volume* matters: does it decay faster with the ROS 2
   stack running than with the board idle?
4. Only then look at `task_communication.c`

**Consequence meanwhile:** Madgwick is configured `frequency: 50.0` and the EKF
now runs at 50 Hz. Both are being fed ~40 Hz after a few hours. Phase 4 must not
tune `gain`/`zeta` against an input rate that depends on how long ago someone
power-cycled the board.

---

### HW-BUG-1: EKF Output Rate ~2.5 Hz Instead of Configured 25 Hz
**Opened:** 2026-03-25 · **NOT REPRODUCIBLE on the Beelink, 2026-08-03**
**Severity:** ~~MEDIUM~~ — see the resolution note below

> **Measured 2026-08-03 on the Beelink SER5 Pro:** `/odometry/filtered` runs at
> **24.0–24.5 Hz** against a configured 25.0 — within 4 %. Robot elevated,
> motors disabled, full `robot.launch.py` stack up, whole machine at 1.3 % CPU.
>
> **Re-confirmed 2026-08-04 at a higher setpoint.** The EKF was re-derived from
> its input rates and now runs at **50 Hz** (see [[inherited-values]]);
> `/odometry/filtered` measured **49.999 Hz** — within 0.002 %, at double the
> rate that originally failed. `ekf_node` costs 1.6 % of one core. Whatever the
> Pi could not sustain, this machine sustains twice as much without noticing.
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
