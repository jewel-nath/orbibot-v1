---
title: "Roadmap"
type: plan
tags:
  - plan
  - roadmap
---

# Roadmap to a stable indoor autonomous robot

Seven phases. Each ends at a **gate made of numbers**, not opinions. You do not
start the next phase until the current gate is met — every phase assumes the
ones under it are true, and a shaky base does not get less shaky when you put
navigation on top of it.

Rewritten 2026-08-03 against the current codebase.

---

## Where the robot actually is

**Solid, and verified live** — `test-report.md`, dated sections:

| | |
|---|---|
| Serial protocol | Round-trips, rejects malformed input, survives 500 Hz for 3 s |
| Mecanum kinematics | All four directions correct, wheels-free |
| Command timeout | Motors stop 2.12 s after the last command |
| Velocity clamp | Peak 1023 mm/s on a 3000 mm/s command |
| Battery | 12.5 V, in range |
| Accelerometer | `\|a\| = 9.802 m/s²`, ratio to g **0.9995** (2026-08-03) |
| Raw IMU | 52.5 Hz, 12-byte packets, matching the driver |

**Not solid:**

- Nothing on this robot has been calibrated **on the ground**. Every motion
  number above was taken with the wheels free.
- Heading has no absolute reference since the magnetometer was removed, and
  nothing has measured how fast yaw drifts without it.
- Four things publish `/cmd_vel` and nothing arbitrates — [[command-pipeline]].
- Accel X and Y scale is unconfirmed under real acceleration — [[backlog-moc]] CC-2.
- `MAX_WHEEL_SPEED_MMS` is theoretical, and M4 runs 12–15 % slower than M1–M3
  (`firmware-issue.md`, FW-ISSUE-4).

**Suspect:** any localisation figure recorded before 2026-08-03. Two faults were
feeding the estimator bad data — an inflated accelerometer Z, and a raw-IMU path
silently dropped by a length check. Re-measure; do not trust.

---

## Principles

1. **Measure on the ground.** Wheels-free proves direction and sign. It cannot
   prove distance, drift or traction.
2. **One number, written down.** A measurement left in the terminal gets
   re-measured next month. Date it, and record what state the robot was in.
3. **Fix the cause, not the reading.** The accelerometer taught this expensively:
   a compensation factor hid a misconfigured register for four months, and made
   two axes worse while making the third look right.
4. **Nothing gets built on an unmet gate.**

---

## Phase 1 — Trust the base

Everything above this reads odometry and IMU. If they lie, so does everything
else.

| # | Task | Robot state |
|---|---|---|
| 1.1 | Wheel radius and encoder CPR — drive a measured 2 m, compare `/odom` | ground, ~3 m clear |
| 1.2 | Rotation — 10 × 360° in place, compare accumulated yaw | ground, ~1.5 m clear |
| 1.3 | **Yaw drift rate**, stationary, 10 min — the number that replaces the magnetometer | ground, still |
| 1.4 | Forward/backward velocity asymmetry seen wheels-free | ground |
| 1.5 | Accel X/Y scale under a known acceleration (CC-2) | ground |
| 1.6 | Re-tune motor PID under load; write it to flash | ground |
| 1.7 | Measure real max wheel speed per motor; decide whether M4's 12–15 % deficit is mechanical or PID | elevated, then ground |
| 1.8 | Host-side unit tests — kinematics, PID, odometry, protocol state machine | no robot |
| 1.9 | One source of truth for the protocol table — firmware, driver and tests keep three hand-maintained copies | no robot |

**Sensible order:** 1.8 and 1.9 first — no hardware needed, and 1.9 removes the
class of bug that once cost a whole sensor. Then 1.1–1.5 in a single clear-floor
session. Then 1.6 and 1.7.

**Gate**

- Straight 2 m: odometry error **< 3 %**, forward and backward
- 10 × 360°: accumulated yaw error **< 5°** total
- Yaw drift, stationary, 10 min: **recorded** — a baseline, not a pass/fail, but
  Phase 4 cannot be judged without it
- Forward and backward at equal commanded speed agree within **5 %**
- `\|a\|` within **1 %** of g through a slow tilt, on all three axes
- Unit tests green with no hardware attached

---

## Phase 2 — Safe command pipeline

Teleop is web-only, so **the network is the control path**. A dropped wifi link
must not be a runaway robot.

| # | Task |
|---|---|
| 2.1 | `apt install ros-jazzy-twist-mux` — **not** `joy`; teleop is web-only |
| 2.2 | Move all four publishers off `/cmd_vel` onto their own topics |
| 2.3 | Configure priorities and **per-input timeouts** |
| 2.4 | An e-stop topic at top priority, wired to the dashboard |
| 2.5 | Publish and display which source is currently driving |
| 2.6 | Evaluate the unused PD2 button as a hardware e-stop |

**Gate** — the acceptance tests in [[command-pipeline]], in particular:

- Exactly **one** publisher on `/cmd_vel`: `twist_mux`
- Robot stops within **0.3 s** of the commanding input going silent
- **Pull the wifi mid-drive.** The robot stops. This is the test that matters.

---

## Phase 3 — Dashboard and the teleop demo ⭐

The milestone worth showing: drive the robot around a room from the browser with
a controller, before any autonomy exists.

| # | Task |
|---|---|
| 3.1 | Aggregate the telemetry subscriptions into one 5–10 Hz message |
| 3.2 | Decimate `/scan` for the browser; serve `/map` on request, not on a topic |
| 3.3 | Camera via v4l2 → WebRTC, **never through ROS** |
| 3.4 | Browser Gamepad API → `/cmd_vel_web` |
| 3.5 | Serve the built `dist/` — never the Vite dev server on the Pi |
| 3.6 | Show the active `cmd_vel` source, always |

**Gate**

- Drive a full room from the dashboard, on a controller
- Dashboard backend **< 10 % CPU**; whole stack **< 40 %**
- Telemetry latency **< 200 ms**
- Releasing the stick stops the robot in under 0.3 s

Design and CPU budget: [[dashboard-design]].

---

## Phase 4 — Localisation quality

Only meaningful once Phase 1's numbers exist to compare against.

| # | Task |
|---|---|
| 4.1 | Re-measure IMU noise; set EKF covariances from data, not defaults |
| 4.2 | Tune Madgwick `gain` and `zeta` — with `use_mag: false`, `zeta` is what fights gyro bias |
| 4.3 | Compare `/odom` against `/odometry/filtered` over a closed loop |
| 4.4 | Confirm the EKF publishes at its configured rate |

**Gate**

- Closed 4 m × 4 m loop: final position error **< 5 %** of path length
- `/odometry/filtered` measurably better than raw `/odom` on the same run
- EKF output rate within **10 %** of configured

---

## Phase 5 — Mapping

| # | Task |
|---|---|
| 5.1 | slam_toolbox parameters for a 10 Hz, 8 m A1 |
| 5.2 | Map a real room, save it |
| 5.3 | Confirm exactly one node publishes `map → odom` |
| 5.4 | Re-localise against the saved map from a cold start |

**Gate**

- A room map with no double walls and no visible drift at loop closure
- Cold-start re-localisation succeeds within 30 s
- CPU headroom left for Nav2

---

## Phase 6 — Autonomous navigation

The Nav2 config was written for a Pi 4. **Re-measure every limit before trusting
it.**

| # | Task |
|---|---|
| 6.1 | Re-derive velocity and acceleration limits from Phase 1's measured maxima |
| 6.2 | MPPI with the `Omni` motion model; confirm it actually strafes |
| 6.3 | Footprint and inflation against the real 350 × 250 mm chassis |
| 6.4 | Collision monitor tuned to the A1's blind zone |
| 6.5 | Goal-to-goal across a room with obstacles |

**Gate**

- Ten consecutive goals reached with no human intervention
- No contact with any obstacle
- Recovery behaviours fire and succeed when deliberately blocked

---

## Phase 7 — Exploration and AI

| # | Task |
|---|---|
| 7.1 | Frontier explorer against the tuned Nav2 |
| 7.2 | Termination when no reachable frontier remains |
| 7.3 | Agent tools driving through the arbitrated pipeline, never `/cmd_vel` directly |
| 7.4 | Agent motion at low priority, below the dashboard's |

**Gate** — explore an unknown floor to completion with no human input, then
navigate the map it built.

---

## What to delete or redesign, versus what to fix

| Thing | Verdict |
|---|---|
| Direct `/cmd_vel` from four nodes | **Redesign** — Phase 2 |
| RealSense as a full RGB-D sensor on the Pi | **Redesign** — webcam over WebRTC only, until a mini PC |
| Magnetometer | **Deleted** 2026-04-28, correctly. Indoors it made heading worse |
| Gazebo | **Deleted** 2026-08-03. The Pi is the robot |
| `orbibot_teleop` | **Keep, dormant.** A network-independent fallback. Do not install `joy` |
| Three hand-maintained protocol tables | **Redesign** — 1.9 |
| Nav2 parameters | **Fix in place**, after re-measuring |
| Firmware PID, encoders, protocol | **Fix in place.** Structurally sound |

---

## Working with Fable 5

The next session executes this. It should:

- Take Phase 1 tasks one at a time, in order, and not skip ahead
- Ask for **one physical action at a time**, then wait — jumper, robot down,
  space cleared
- Build before asking for a jumper; never spend the operator's hands on a build
  that fails
- Report numbers, not adjectives, and write them into `test-report.md`
- Commit each task together with its measurement

Rules it must read first: `.claude/rules/robot-safety.md`.

## Related

[[docs/README|Docs home]] · [[backlog-moc]] · [[command-pipeline]] ·
[[dashboard-design]] · [[system-overview]] · [[next-session-prompt]]
