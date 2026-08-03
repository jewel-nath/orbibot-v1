---
title: "Roadmap"
type: plan
tags:
  - plan
  - roadmap
---

# Roadmap to a stable indoor autonomous robot

Nine phases. Each ends at a **gate made of numbers**, not opinions. You do not
start the next phase until the current gate is met — every phase assumes the
ones under it are true, and a shaky base does not get less shaky when you put
navigation on top of it.

Rewritten 2026-08-03 against the current codebase, then again the same day when
the compute was replaced.

---

## Where the robot actually is

**The computer changed on 2026-08-03.** A Raspberry Pi 5 ran this stack until
it saturated all four cores under any real workload — SLAM, Nav2, the
dashboard, the camera — which made the robot uncontrollable rather than merely
slow. It is replaced by a **Beelink SER5 Pro**: 8C/16T Ryzen 7 PRO 5800H,
11.6 GiB, 457 G NVMe, x86_64. Roughly 4–6× the CPU.

The Pi's state is preserved on the `raspberry_pi` branch. Do not delete it.

**Solid, and verified live** — `test-report.md`, dated sections. All of this is
firmware-side, so **the host swap does not invalidate any of it**:

| | |
|---|---|
| Serial protocol | Round-trips, rejects malformed input, survives 500 Hz for 3 s |
| Mecanum kinematics | All four directions correct, wheels-free |
| Command timeout | Motors stop 2.12 s after the last command |
| Velocity clamp | Peak 1023 mm/s on a 3000 mm/s command |
| Battery | 12.5 V, in range |
| Accelerometer | `\|a\| = 9.802 m/s²`, ratio to g **0.9995** (2026-08-03) |
| Raw IMU | 52.5 Hz, 12-byte packets, matching the driver |

That the firmware survived a complete change of host is the architecture
working as designed — see [[system-overview]].

**Not solid:**

- **The Beelink is not mounted and not set up.** No ROS 2, no toolchain, no
  hardware attached. [[computer-setup]] is Phase 0.
- **The robot's mass and centre of gravity are about to change.** Every Phase 1
  number must be taken *after* the Beelink and its converter are bolted on.
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

**Void, not merely suspect:** every CPU-derived tuning value. The "reduced for
Raspberry Pi" comments in `nav2_params.yaml` and `slam_params.yaml`, and the
budget table in [[dashboard-design]], were fitted to hardware that is gone.
They must be re-derived from a measured baseline, not scaled by a guessed
ratio.

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
5. **A number inherited from different hardware is not a number.** Delete it
   and re-measure. Rescaling it produces something that looks measured and is
   not — which is worse than an empty cell.

---

## Phase 0 — The new machine ⬅ **you are here**

Nothing else can start. The computer is on a bench, not on the robot, and it
has an operating system and nothing else.

| # | Task | Where |
|---|---|---|
| ~~0.1~~ | ~~Confirm supply voltage from the adapter label~~ — **done: 19 V / 3.42 A** | bench |
| 0.2 | Set the boost converter output with a multimeter *before* connecting it | bench |
| 0.3 | Install ROS 2 Jazzy, toolchain, `twist_mux`, RealSense driver | — |
| 0.4 | `rosdep` + `colcon build` — 12 packages clean on x86_64 | — |
| 0.5 | udev rules; `/dev/motordriver` and `/dev/lidar` appear on boot | — |
| 0.6 | RealSense enumerates at **5000 Mbps**, depth + colour together | — |
| 0.7 | PlatformIO toolchain; firmware builds; fix the `pio` path in the docs | — |
| 0.8 | Mount the Beelink, converter and fuse on the robot | robot |
| 0.9 | **Re-weigh the robot and re-measure the footprint** | robot |
| 0.10 | Power measurements P-1…P-5 — sag, thermals, brown-out | robot |
| 0.11 | **Record a CPU and thermal baseline** — stack idle, and stack driving | robot |

Full procedure, including the wiring order that matters: [[computer-setup]].

**Gate**

- ~~Adapter label read~~ — **done, 19 V / 3.42 A**. Converter output verified at 19.0 V before the Beelink is connected
- Battery rail stays **> 11.5 V** and converter output **> 18 V** through a
  four-motor full-speed burst
- Ten motor start/stop cycles with the Beelink logged in: **no reboot**, no
  reset in `dmesg`
- `colcon build` clean, **12 packages**
- `ros2 launch orbibot_bringup robot.launch.py` runs: `/scan` at 10 Hz, `/odom`
  publishing
- RealSense at **5000 Mbps** with depth and colour streaming together
- New mass and footprint written into [[inventory]]
- CPU baseline recorded — Phases 3 and 6 have nothing to budget against without it

> 0.10 is the one people skip. A brown-out during an NVMe write corrupts the
> filesystem, and the converter's 10 V minimum sits only 0.5 V below the BMS
> cutoff. Measure it before trusting the robot to drive itself anywhere.

---

## Phase 1 — Trust the base

Everything above this reads odometry and IMU. If they lie, so does everything
else.

**Prerequisite: 0.8 and 0.9.** Calibrating before the Beelink is bolted on
produces numbers that are wrong the moment the robot is assembled — mass and
centre of gravity feed traction, PID response and odometry directly.

| # | Task | Robot state |
|---|---|---|
| 1.1 | Wheel radius and encoder CPR — drive a measured 2 m, compare `/odom` | ground, ~3 m clear |
| 1.2 | Rotation — 10 × 360° in place, compare accumulated yaw | ground, ~1.5 m clear |
| 1.3 | **Yaw drift rate**, stationary, 10 min — the number that replaces the magnetometer | ground, still |
| 1.4 | Forward/backward velocity asymmetry seen wheels-free | ground |
| 1.5 | Accel X/Y scale under a known acceleration (CC-2) | ground |
| 1.6 | Re-tune motor PID **under the new mass**; write it to flash | ground |
| 1.7 | Measure real max wheel speed per motor; decide whether M4's 12–15 % deficit is mechanical or PID | elevated, then ground |
| 1.8 | Host-side unit tests — kinematics, PID, odometry, protocol state machine | no robot |
| 1.9 | One source of truth for the protocol table — firmware, driver and tests keep three hand-maintained copies | no robot |

**Sensible order:** 1.8 and 1.9 first — no hardware needed, and 1.9 removes the
class of bug that once cost a whole sensor. They can also be done *during*
Phase 0, while waiting on parts. Then 1.1–1.5 in a single clear-floor session.
Then 1.6 and 1.7.

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

2.1 folds into Phase 0's install list — do not let it be forgotten again. It
was missing on the Pi for the whole of that machine's life.

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
| 3.3 | Camera to WebRTC — via the RealSense driver now that depth is on, ideally as a composable node |
| 3.4 | Browser Gamepad API → `/cmd_vel_web` |
| 3.5 | Serve the built `dist/` — never the Vite dev server on the robot |
| 3.6 | Show the active `cmd_vel` source, always |

3.1 and 3.2 are still worth doing on a fast machine. They were never really
about CPU — they are about bytes over WiFi, work in the operator's browser, and
having one explicit data contract instead of fifteen scattered hooks. See
[[dashboard-design]].

**Gate**

- Drive a full room from the dashboard, on a controller
- Telemetry latency **< 200 ms**
- Camera latency **< 300 ms**
- Releasing the stick stops the robot in under 0.3 s
- CPU **measured against the Phase 0 baseline** — the old "< 10 % / < 40 %"
  targets were Pi fractions and are meaningless here. Set real ones once 0.11
  exists

---

## Phase 4 — Localisation quality

Only meaningful once Phase 1's numbers exist to compare against.

| # | Task |
|---|---|
| 4.1 | Re-measure IMU noise; set EKF covariances from data, not defaults |
| 4.2 | Tune Madgwick `gain` and `zeta` — with `use_mag: false`, `zeta` is what fights gyro bias |
| 4.3 | Compare `/odom` against `/odometry/filtered` over a closed loop |
| 4.4 | Confirm the EKF publishes at its configured rate |
| 4.5 | Reconsider the EKF rate — 25 Hz was a Pi compromise, not a design choice |

**Gate**

- Closed 4 m × 4 m loop: final position error **< 5 %** of path length
- `/odometry/filtered` measurably better than raw `/odom` on the same run
- EKF output rate within **10 %** of configured

---

## Phase 5 — Mapping

| # | Task |
|---|---|
| 5.1 | slam_toolbox parameters for a 10 Hz, 8 m A1 — **delete the "optimized for Raspberry Pi" values and re-derive** |
| 5.2 | Map a real room, save it |
| 5.3 | Confirm exactly one node publishes `map → odom` |
| 5.4 | Re-localise against the saved map from a cold start |

**Gate**

- A room map with no double walls and no visible drift at loop closure
- Cold-start re-localisation succeeds within 30 s
- CPU headroom left for Nav2, measured not assumed

---

## Phase 6 — Autonomous navigation

The Nav2 config was written for a Pi 4, then run on a Pi 5, and is now on a
machine with four times the cores. **Re-derive every limit; do not trust one.**

| # | Task |
|---|---|
| 6.1 | Re-derive velocity and acceleration limits from Phase 1's measured maxima |
| 6.2 | Raise `controller_frequency` (5.0) and MPPI `batch_size` (500) — both were cut for the Pi |
| 6.3 | MPPI with the `Omni` motion model; confirm it actually strafes |
| 6.4 | Footprint and inflation against the **re-measured** chassis from 0.9 |
| 6.5 | Collision monitor tuned to the A1's blind zone |
| 6.6 | Bring depth into the costmap — a voxel or STVL layer from `/camera/depth/*` |
| 6.7 | Goal-to-goal across a room with obstacles |

6.6 is new and only possible now. The A1 is a 2D scanner at one height: it
cannot see a table top, a step, or anything below its plane. Depth fixes the
class of obstacle that a 2D lidar structurally cannot detect.

**Gate**

- Ten consecutive goals reached with no human intervention
- No contact with any obstacle
- **An obstacle invisible to the lidar** — a table top, a low box — is avoided
  using depth
- Recovery behaviours fire and succeed when deliberately blocked

---

## Phase 7 — Exploration

| # | Task |
|---|---|
| 7.1 | Frontier explorer against the tuned Nav2 |
| 7.2 | Termination when no reachable frontier remains |
| 7.3 | Recovery when a frontier turns out to be unreachable |

**Gate** — explore an unknown floor to completion with no human input, then
navigate the map it built.

---

## Phase 8 — The agentic layer

`orbibot_agent` already exists: multi-LLM, 62 tools, an HTTP API, a CLI and an
MCP server, talking to ROS 2 through a native bridge. What it does not have is
a **safe place in the control hierarchy** or any way to tell whether it is
behaving.

| # | Task |
|---|---|
| 8.1 | Move `core/ros_bridge/motion.py` off `/cmd_vel` onto its own arbitrated topic |
| 8.2 | Agent motion at a priority **below the dashboard's** — a human always wins |
| 8.3 | Natural language → Nav2 goal, through the pipeline, never direct |
| 8.4 | Semantic layer — depth + detection, so "go to the kitchen" resolves to a pose |
| 8.5 | Bound the agent: no motion command it cannot justify, every one logged |
| 8.6 | A scripted evaluation set with pass criteria, not vibes |

**8.2 is the safety property of this whole phase.** An LLM in the control loop
is a publisher that can be confidently wrong. It gets the lowest priority and
the shortest timeout of anything that moves the robot, and the operator's stick
must always preempt it — that is what [[command-pipeline]] is for.

**Gate**

- Every agent motion path goes through `twist_mux`; **zero** direct `/cmd_vel`
  publishers, verified by grep and by `ros2 topic info`
- Operator input overrides an agent-commanded motion within **0.3 s**, measured
- A fixed scenario set — *"go to the kitchen"*, *"explore this floor"*,
  *"come back to where you started"* — passes **N of N** runs, with N and the
  scenarios written down before the run, not after
- The agent refuses or asks rather than guessing when a goal is unresolvable

---

## Optional — Simulation

Not on the critical path, and deliberately not numbered. It became *possible*
with this machine (Ryzen 7 + Vega iGPU) where it was not on a Pi, and it can be
added at any point without rework.

Ubuntu Server is not an obstacle: `gz sim -s` runs headless, Mesa gives EGL
sensor rendering on the iGPU, and the GUI plus RViz run on the operator's
laptop over the network.

**Worth it when** Phase 6 or 7 iteration starts costing more in cleared floor
space and operator time than a simulator would cost to stand up. Tuning MPPI or
a frontier explorer against a simulated room is faster and cannot break a real
robot. `orbibot_gazebo` was deleted on the reasoning that "the Pi is the robot";
that reasoning no longer applies, but the decision stands until someone needs it.

---

## What to delete or redesign, versus what to fix

| Thing | Verdict |
|---|---|
| Direct `/cmd_vel` from four nodes | **Redesign** — Phase 2 |
| Raspberry Pi 5 | **Removed** 2026-08-03. Preserved on the `raspberry_pi` branch |
| Every "reduced for Raspberry Pi" tuning value | **Delete and re-derive.** Do not rescale |
| RealSense depth | **Enabled** 2026-08-03. Was blocked by the Pi's CPU and a USB 2.0 link; both are gone |
| The v4l2 camera bypass in [[dashboard-design]] | **Superseded.** Depth means the driver owns the device |
| Magnetometer | **Deleted** 2026-04-28, correctly. Indoors it made heading worse |
| Gazebo | **Deleted** 2026-08-03. Re-openable — see *Optional* above |
| `orbibot_teleop` | **Keep, dormant.** A network-independent fallback. Do not install `joy` |
| Three hand-maintained protocol tables | **Redesign** — 1.9 |
| Nav2 parameters | **Fix in place**, after re-measuring — Phase 6 |
| Firmware PID, encoders, protocol | **Fix in place.** Structurally sound, and survived the host swap untouched |

---

## Working through this

Each phase, one task at a time, in order. For every task:

- Ask for **one physical action at a time**, then wait — jumper, robot down,
  space cleared
- Build before asking for a jumper; never spend the operator's hands on a build
  that fails
- Report numbers, not adjectives, and write them into `test-report.md`
- Commit each task together with its measurement

Rules to read first: `.claude/rules/robot-safety.md`.

## Related

[[docs/README|Docs home]] · [[computer-setup]] · [[backlog-moc]] ·
[[command-pipeline]] · [[dashboard-design]] · [[system-overview]] ·
[[next-session-prompt]]
