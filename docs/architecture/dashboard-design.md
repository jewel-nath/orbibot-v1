# Dashboard Design

A dashboard that shows everything and controls everything, while leaving the
Pi 5 enough CPU to run Nav2. The constraint is not rendering — that happens in
the operator's browser — it is **what the Pi has to serialise and send**.

**Status: designed, not built.** The dashboard that runs today is described in
[orbibot_webgui](../../src/orbibot_webgui/README.md); this page is the plan for making it cheaper. Its CPU and
bandwidth figures are estimates, not measurements.

---

## The three costs

Everything expensive falls into one of these:

1. **DDS traffic** — moving data between ROS nodes on the Pi
2. **rosbridge serialisation** — turning ROS messages into JSON, per subscriber
3. **Encoding** — turning camera frames into something a browser can show

Each has a different right answer, so they get separate channels.

## Channel 1 — Telemetry (low rate, JSON is fine)

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

## Channel 2 — Visualisation (needs shaping, never raw)

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

## Channel 3 — Camera (never through ROS)

The camera is used as a **plain webcam** — colour only. Depth stays off until
the robot has a machine that can afford it.

Today's path is expensive:

```
D435 → realsense2_camera → /camera/color/image_raw → WebRTC node → browser
```

At 640×480 that topic is 921,600 bytes per frame; at 15 Hz it is **~14 MB/s
pushed through DDS** purely to hand frames to a node that re-encodes them.

**Do instead**: read the D435's UVC node directly with v4l2/GStreamer inside
the WebRTC server, and drop `realsense2_camera` from the graph entirely.

```
D435 (/dev/videoN, UVC) → GStreamer → WebRTC → browser
```

The D435 already exposes `/dev/video0`–`/dev/video5`. Confirm which one carries
colour before wiring it:

```bash
sudo apt install v4l-utils
for v in /dev/video{0..5}; do echo "--- $v"; v4l2-ctl -d $v --list-formats; done
```

If ROS ever needs an image — the agent's planned vision tools — add an
**on-demand snapshot service**, not a continuous stream.

> The camera being on a 480 Mbps link (see [Hardware](../hardware/README.md)) does not block this.
> USB 2.0 is fine for a single colour stream. Moving it to a blue port is
> worth doing when convenient, and becomes required only if depth is revived.

## Serving the frontend

`npm run dev` runs Vite with HMR and a file watcher — a development tool, not
a way to serve a robot dashboard. Build once and serve the static bundle:

```bash
npm run build          # tsc -b && vite build  →  dist/
```

Serve `dist/` from any static server. The Pi then spends nothing on the
frontend; it only answers rosbridge and WebRTC.

## Controls the dashboard must own

| Control | Publishes / calls |
|---|---|
| Drive (on-screen joystick + browser Gamepad API) | `/cmd_vel_web` — see [Command Pipeline](command-pipeline.md) |
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
[Command Pipeline](command-pipeline.md).

## Budget to hold

Measure, do not assume. Targets on the Pi 5 while driving:

| | Target |
|---|---|
| Total CPU with dashboard + teleop | < 40 % of 4 cores |
| Total CPU with dashboard + Nav2 + SLAM | < 75 % |
| Dashboard's own share | < 10 % |
| Telemetry latency, sensor → screen | < 200 ms |
| Camera latency | < 300 ms |
| Temperature under load | < 70 °C, `throttled=0x0` |

Record real numbers as they are measured — a budget nobody checks is decoration.

## Related

[Command Pipeline](command-pipeline.md) · [orbibot_webgui](../../src/orbibot_webgui/README.md) · [Hardware](../hardware/README.md)
