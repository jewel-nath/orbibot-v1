---
title: "Dashboard Design"
type: architecture
tags:
  - architecture
  - webgui
  - performance
---

# Dashboard Design

A dashboard that shows everything and controls everything, while leaving the
robot's computer enough CPU to run Nav2. The constraint is not rendering — that
happens in the operator's browser — it is **what the robot has to serialise and
send**.

> **Rewritten in part on 2026-08-03**, when the Raspberry Pi 5 was replaced by
> a Beelink SER5 Pro — see [[beelink-bringup]].
>
> Much of this document was written against a machine with four cores that was
> already at 100 %. Some of that advice was really about CPU and is now
> obsolete; some of it was about **network bytes, browser work and having an
> explicit data contract**, and survives untouched. They are marked below, and
> the distinction is worth respecting — deleting the second kind because "we
> have CPU now" would be a mistake.
>
> **Every number in the budget section is void.** They were fitted to the Pi.

---

## The three costs

Everything expensive falls into one of these:

1. **DDS traffic** — moving data between ROS nodes on the Pi
2. **rosbridge serialisation** — turning ROS messages into JSON, per subscriber
3. **Encoding** — turning camera frames into something a browser can show

Each has a different right answer, so they get separate channels.

## Channel 1 — Telemetry (low rate, JSON is fine) · **still correct**

Not a CPU workaround. Fifteen rosbridge subscriptions is fifteen independent
serialisations *and* fifteen scattered places where the dashboard's data
contract lives. The extra cores fix the first problem and not the second.

Battery, motor state, safety flags, odom pose, IMU roll/pitch/yaw, CPU, RAM,
temperature, active `cmd_vel` source, Nav2 state.

The dashboard currently opens a separate rosbridge subscription per value —
around fifteen of them, each independently serialised. Most carry a handful of
numbers.

**Do instead**: one `orbibot_dashboard_bridge` node that subscribes locally
(cheap, intra-process DDS), packs everything into a single message, and
publishes it at a fixed **5–10 Hz**. The browser makes *one* subscription.

This is the single biggest win available. It cuts rosbridge work by roughly the
number of topics collapsed, and it makes the dashboard's data contract explicit
instead of scattered across fifteen hooks.

It also decouples display rate from sensor rate: the IMU can run at 50 Hz for
the EKF while the dashboard sees 10 Hz, which is already faster than anyone can
read.

## Channel 2 — Visualisation (needs shaping, never raw) · **still correct**

The cost here is bytes on the wire and JSON parsing **in the operator's
browser**, over WiFi. A faster robot computer changes neither.

**LiDAR.** `/scan` is ~360 floats at 10 Hz. As JSON that is tens of KB per
second of pure serialisation and parse. Send a **decimated, quantised** scan
instead — every Nth ray, ranges as `uint16` centimetres — inside the same
bridge node. A 120-point scan at 10 Hz is plenty to draw a room and is roughly
an order of magnitude less work.

**Map.** An occupancy grid is large and mostly static. Do not stream it. Serve
it **on request** and after that send only updates, or re-send at something
like 0.5 Hz while mapping. Encoding the grid as PNG is far smaller than a JSON
array of every cell.

**Robot pose** rides in the telemetry channel; the map does not need to move
for the robot to move.

## Channel 3 — Camera · **superseded — the premise changed**

This section previously said: never put the camera through ROS, bypass
`realsense2_camera`, read `/dev/videoN` with v4l2 inside the WebRTC server. It
was right for a four-core Pi on a USB 2.0 link with depth switched off.

**Depth was enabled by decision on 2026-08-03**, and that invalidates the
bypass — for a reason that has nothing to do with CPU.

### The conflict

A V4L2 device has **one owner**. When `realsense2_camera` opens the D435 to
produce depth, librealsense claims the UVC nodes, and a second process cannot
grab `/dev/videoN` for colour. So this is not available:

```
D435 ──► realsense2_camera ──► /camera/depth/*      (perception)
    └──► v4l2 ──► WebRTC ──► browser                ✗ device already claimed
```

Wanting depth means the driver is in the graph, and everything that wants
pixels — including the dashboard — has to go through it.

### What to do instead

```
D435 ──► realsense2_camera ──┬──► /camera/depth/*        perception, Phase 6
                             └──► /camera/color/*  ──►  WebRTC ──► browser
```

The old objection was that this pushes ~14 MB/s through DDS at 640×480/15 Hz.
That number is unchanged, but its meaning is: it was a large fraction of a Pi
and is a small fraction of a Ryzen 7 with 16 threads. Two things make it
cheaper still, and both are worth doing:

- **Run the WebRTC encoder as a composable node in the driver's container**, so
  intra-process comms hands over a pointer instead of copying a frame.
- **Failing that, subscribe via `image_transport`** and let the driver publish
  compressed — the browser needs re-encoded frames regardless.

**Unchanged and still right:** do not serialise image topics through rosbridge
as JSON. WebRTC exists for exactly this. And if ROS needs a still — the agent's
vision tools — use an **on-demand snapshot service**, not another continuous
subscriber.

### Alternative worth considering

If the dashboard's video and the perception pipeline end up fighting for
frame rate or latency, **a second cheap USB webcam for the dashboard** cleanly
separates them and costs less than the engineering to share one device. The
Beelink has the USB bandwidth and the CPU. Not needed yet; note it before
building something clever.

### Prerequisite

Depth needs a real USB 3 link. Confirm **5000 Mbps**, not 480 — blue port,
USB 3-rated cable, and check with the snippet in [[inventory]]. Below that the
driver silently drops stream combinations, and this whole section is moot.

## Serving the frontend

`npm run dev` runs Vite with HMR and a file watcher — a development tool, not
a way to serve a robot dashboard. Build once and serve the static bundle:

```bash
npm run build          # tsc -b && vite build  →  dist/
```

Serve `dist/` from any static server. The robot then spends nothing on the
frontend; it only answers rosbridge and WebRTC. **This rule survives the
hardware change** — it was never really about CPU. A dev server on a robot is a
file watcher and a rebuild loop wired into the control path.

## Controls the dashboard must own

| Control | Publishes / calls |
|---|---|
| Drive (on-screen joystick + browser Gamepad API) | `/cmd_vel_web` — see [[command-pipeline]] |
| Emergency stop | `/cmd_vel_estop`, top priority |
| Motor enable | `SetMotorEnable` |
| Reset odometry / encoders | `ResetOdometry`, `ResetEncoders` |
| PID tuning + save to flash | `FUNC_SET_MOTOR_PID` (0x13) — single PID; multi-level was dropped |
| IMU calibration | `CalibrateIMU` |
| Nav goal / initial pose | `/goal_pose`, `/initialpose` |
| Mapping start / save | slam_toolbox services |
| Exploration | `/orbibot/exploration/command` |

The **active `cmd_vel` source must be displayed at all times**. An operator
should never have to guess whether the robot is under their control or Nav2's.

## Gamepad — the demo milestone

Teleop is **web-only**. A controller plugged into the operator's laptop, read
by the browser's **Gamepad API**, published to `/cmd_vel_web` over rosbridge.
Nothing to install on the Pi.

Ship the on-screen joystick too — `react-joystick-component` is already a
dependency — so the robot is drivable from a phone or from a laptop with no
controller attached.

Requirements that follow from the network being in the control loop:

- **Publish at a steady rate while a control is held** (20 Hz is plenty), not
  only on change. `twist_mux` decides a source is gone by silence, so a held
  stick must keep talking.
- **Publish an explicit zero on release**, then stop. Do not rely on the
  timeout for the normal case — the timeout is for failures.
- **Stop publishing on `blur`, `visibilitychange` and disconnect.** A
  backgrounded tab must look exactly like a crashed one.
- **Show the round-trip latency**, and warn the operator when it climbs. They
  are steering through it.

`orbibot_teleop` (Pi-side `/joy`) is deliberately not wired up — see
[[command-pipeline]].

## Budget to hold — **void, pending a new baseline**

The table that used to be here read *"< 40 % of 4 cores"*, *"< 75 %"*,
*"throttled=0x0"*. Every one of those was a Pi 5 number, and the last is a
`vcgencmd` idiom that does not exist on x86 at all.

**Do not translate them.** A budget derived by scaling old numbers by a guessed
core ratio is worse than no budget: it looks measured and is not. The Phase 0
gate in [[beelink-bringup]] requires a fresh baseline on the Beelink — stack
idle, and stack driving — and the real targets get written here from that.

What survives, because it is about the operator and not the hardware:

| | Target |
|---|---|
| Telemetry latency, sensor → screen | < 200 ms |
| Camera latency | < 300 ms |
| Stick released → robot stopped | < 0.3 s |

Latency budgets are perceptual. They did not change because the computer did.

The CPU and thermal rows to be filled in once measured:

| | Measured | Target |
|---|---|---|
| Whole stack idle | — | — |
| Dashboard + teleop | — | — |
| Dashboard + Nav2 + SLAM + depth | — | — |
| Dashboard's own share | — | — |
| CPU package temperature under load | — | — |

Thermals on this machine are read with `sensors` (`lm-sensors`) or
`/sys/class/thermal/thermal_zone*/temp`, and sustained-clock behaviour from
`/proc/cpuinfo` — not `vcgencmd`.

Record real numbers as they are measured — a budget nobody checks is decoration.

## Related

[[roadmap]] · [[beelink-bringup]] · [[command-pipeline]] · [[orbibot_webgui]] ·
[[inventory]]
