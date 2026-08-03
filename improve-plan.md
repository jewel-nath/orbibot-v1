# OrbiBot — Improvement Plan

What to improve, why, and what is already settled. Originally written
2026-03-23 as a comparison against `lgdxrobot2` (an open-source mecanum robot
on an STM32F411 with the same ICM-20948 IMU).

**Rewritten 2026-08-03.** Much of the original was overtaken by events: the
magnetometer was deleted, an accelerometer fault was found and fixed, and the
robot's computer was replaced. The comparison is still useful and is kept. The
conclusions drawn from it in March were not all correct, and the wrong ones are
corrected below rather than quietly dropped.

Execution order lives in [[roadmap]]. This document is the *why*.

---

## Corrections — things this document previously got wrong

Kept visible on purpose. `.claude/rules/docs-sync.md` exists because a
confidently wrong note is worse than no note, and three of these shipped as
fact for months.

### ✗ "Motors are uniform — per-motor max speed config not needed"

**This conclusion does not follow from the test that produced it.**

The March measurement drove each motor to a **commanded 1000 mm/s with PID
closing the loop**, and all four landed within ±10 mm/s:

```
M1 (FL) 1000.4    M2 (BL) 1001.3    M3 (FR) 1001.3    M4 (BR) 1000.7  mm/s
```

That is a measurement of **closed-loop tracking at a speed all four motors can
comfortably reach** — not of maximum speed. The same section noted that the
firmware's 1.0 m/s clamp prevented any motor from reaching full PWM, and then
concluded uniformity anyway.

On 2026-04-19, `firmware-issue.md` recorded the opposite from the other
direction: **M4 reports 12–15 % fewer encoder ticks than M1–M3 across every
motion type**, with the PID compensating by feeding it more PWM. Both
observations are true. A motor that needs more PWM for the same speed has less
headroom, and the test that "proved uniformity" was structurally incapable of
seeing it.

**Status: open.** Roadmap 1.7 — measure at full PWM, wheels free, per wheel.
If M4 is >10 % down at no load, it is mechanical: bearings, gear mesh, or wheel
alignment.

### ✗ "Accel Z reads 15.35 m/s² — investigate the scale factor"

**Resolved 2026-08-03, and the original diagnosis was the expensive kind of
wrong.** It was not a scale factor. A register was left misconfigured, and a
compensation factor derived from the wrong explanation shipped for four months
— making two axes worse while making the third look right.

Now verified: `|a| = 9.802 m/s²`, ratio to g **0.9995** (`test-report.md` §9.4).

The lesson is Principle 3 in [[roadmap]]: fix the cause, not the reading.

### ✗ Everything about the magnetometer

Items 14, 15 and "mag calibration flash persistence" are **void**. The
magnetometer was removed on 2026-04-28 across firmware, driver and messages —
indoors, steel and motor currents made heading worse than useless. Madgwick
runs `use_mag: false`. Do not propose bringing it back.

`orbibot_localization/README.md` still describes it — [[backlog-moc]] CC-4.

### ⚠ The measured IMU noise covariances are suspect

```
Accel variance: X=0.000081 Y=0.000053 Z=0.000041 (m/s²)²
Gyro  variance: X=0.000001 Y=0.000026 Z=0.000001 (rad/s)²
```

Measured 2026-03-24 and written into `hardware_params.yaml`. They were taken
**through the faulty accelerometer path**, and through a raw-IMU path that a
length check was silently dropping. Re-measure — [[backlog-moc]] CC-3, roadmap
4.1.

### ⚠ Every CPU-justified conclusion

"EKF 25 Hz — lgdxrobot2 is faster because it uses a C++ node" and similar were
really about the Pi running out of cores. The Pi is gone. Re-derive from a
measured baseline rather than rescaling — roadmap 4.5.

---

## Comparison with lgdxrobot2

Corrected where the March version was wrong. Still the most useful external
reference this project has.

### Architecture

| Feature | OrbiBot | lgdxrobot2 | Better |
|---------|---------|-----------|--------|
| **MCU** | STM32F103RCT6 (72 MHz) | STM32F411 (100 MHz) | lgdx |
| **RTOS** | FreeRTOS, 4 tasks, priorities | Bare-metal timer ISR | **OrbiBot** |
| **Host link** | UART 115200 (~11.5 KB/s) | USB CDC (~12 Mbps) | **lgdx** |
| **Main loop** | 4 tasks at different rates | Single 100 Hz ISR | **OrbiBot** |
| **Watchdog** | IWDG + task alive kicks | None | **OrbiBot** |
| **ROS 2 node** | Python (rclpy) | C++ (rclcpp) | lgdx |

The 115200 baud link is the one real architectural deficit and it is **not**
fixed by the new computer — it is a firmware and cabling property. Worth
revisiting only if telemetry rate becomes a measured bottleneck.

### PID and motor control

| Feature | OrbiBot | lgdxrobot2 | Better |
|---------|---------|-----------|--------|
| **PID type** | Incremental | Positional | Both valid |
| **PID levels** | Single | 3-level speed-interpolated | lgdx |
| **Per-motor gains** | Same for all 4 | Per motor × per level | lgdx |
| **Per-motor max speed** | ⚠ **unmeasured** — see Corrections | Measured: {12.85, 12.06, 11.74, 10.47} rad/s | **lgdx** |
| **Anti-windup** | Conditional integral clamp | Back-calculation | Both good |
| **Tuning tool** | ROS 2 topic | Qt GUI, live chart | lgdx |
| **Flash persistence** | ✅ PID | ✅ PID + max speed | Both |
| **Velocity ramp** | Asymmetric — instant accel, gradual decel | Symmetric 0.1 rad/s/tick | **OrbiBot** |
| **Yaw PID** | ✅ IMU heading compensation | None | **OrbiBot** |
| **Command timeout** | ✅ 2 s, verified live | None | **OrbiBot** |

### Odometry

| Feature | OrbiBot | lgdxrobot2 | Better |
|---------|---------|-----------|--------|
| **Integration** | RK2 midpoint | Euler | **OrbiBot** |
| **Covariance** | Adaptive | None | **OrbiBot** |
| **Heartbeat re-publish** | ✅ late joiners | No | **OrbiBot** |
| **Deduplication** | ✅ skip unchanged | No | **OrbiBot** |

RK2 matters when rotation and translation happen together — Euler accumulates
real error on arcs. `odometry.c` takes the midpoint of the heading change
before projecting, which costs one extra multiply.

### Safety

| Feature | OrbiBot | lgdxrobot2 | Better |
|---------|---------|-----------|--------|
| **Software e-stop** | ✅ | ✅ | Both |
| **Hardware e-stop** | Battery lockout only | Dedicated GPIO + DRxSTBY | **lgdx** |
| **Battery low e-stop** | ✅ critical voltage lockout | ✅ | Both |
| **Watchdog** | IWDG | None | **OrbiBot** |
| **Command timeout** | ✅ | None | **OrbiBot** |

lgdx's dedicated e-stop pin is the one safety feature OrbiBot lacks. The
**unused PD2 user button** is the obvious answer and costs no new parts —
roadmap 2.6.

---

## Open items

Ordered by what blocks what, and mapped to [[roadmap]].

| Item | Why | Phase |
|---|---|---|
| **Per-motor max speed, at full PWM** | The March test measured tracking, not capability. M4 is suspect | 1.7 |
| **Re-tune PID under the new mass** | The Beelink and converter change mass and CG. Existing gains were tuned against the Pi's | 1.6 |
| **Re-measure IMU noise** | Existing values came through a faulty accel path | 4.1 |
| **Madgwick `gain` / `zeta`** | With `use_mag: false`, `zeta` is the only thing fighting gyro bias | 4.2 |
| **Accel X/Y scale under real acceleration** | Z is verified static; X and Y read ~0 either way, and those are the axes a ground robot uses | 1.5 (CC-2) |
| **Hardware e-stop on PD2** | The one safety feature lgdxrobot2 has and this does not | 2.6 |
| **`MAX_WHEEL_SPEED_MMS` from measurement** | 3500 is 2× theoretical; too generous a threshold lets EMI spikes through | 1.7 (FW-ISSUE-4) |
| **Firmware IMU variance → ROS 2** | Firmware computes it via Welford and nothing reads the getter | 4.1 (FW-ISSUE-7) |
| **PID tuning page in the dashboard** | lgdx's Qt chassistuner, but in the browser. Now affordable | 3 |

### Deliberately not doing

| Item | Why |
|---|---|
| **PID output normalisation** | lgdx divides PID output by per-motor max speed so gains are motor-independent. Only worth it if motors are replaced |
| **Symmetric velocity ramp** | OrbiBot's asymmetric ramp — instant accel, 10 mm/s/tick decel — is better. lgdx's symmetric ramp slows acceleration for no gain |
| **Euler → anything** | Already RK2, already better |
| **Magnetometer, in any form** | Deleted by decision. See Corrections |

---

## Test commands

```bash
# EKF rate
ros2 topic hz /odometry/filtered

# Accel bias (X, Y should sit near 0 on a level robot)
ros2 topic echo /imu/data_raw --field linear_acceleration --once

# IMU noise (robot stationary, level, 30 s) — re-run, old values are suspect
ros2 run orbibot_localization measure_imu_noise

# Per-motor max speed — ROBOT ELEVATED, wheels free, full PWM
cd src/orbibot_rosmaster_firmware/tests
python3 test_motor_max_speed.py --port /dev/motordriver

# PID step response — robot on the ground, ≥2 m clear
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: true}'
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "linear: {x: 0.3}, angular: {z: 0.0}"
```

Read `.claude/rules/robot-safety.md` before any of the last two.

## Related

[[roadmap]] · [[computer-setup]] · [[backlog-moc]] · [[lgdxrobot2]] ·
[[firmware-architecture]]
