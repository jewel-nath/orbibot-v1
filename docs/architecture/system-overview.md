---
title: "System Overview"
type: architecture
tags:
  - architecture
  - overview
---

# System Overview

Two computers. The STM32 closes the fast loops; the host does everything that
needs a map, a model, or a network.

```
                     ┌─────────────────────────────────────────┐
   RPLidar A1 ──USB──┤   Beelink SER5 Pro   (ROS 2 Jazzy)      │
   RealSense  ─USB3──┤   Ryzen 7 PRO 5800H · 8C/16T · x86_64   │
                     │   Ubuntu 24.04 Server, headless         │
                     └───────────────────┬─────────────────────┘
                        19V │            │ USB serial, 115200
              ┌─────────────┴──────┐     │
              │ RBD-2767 boost     │     │
              │ 12.8V → 19V, 10A F │     │
              └─────────────┬──────┘     │
                            │ 12.8V      │
                     ┌──────┴────────────┴─────────────────────┐
                     │   ROSMaster V3.0 — STM32F103RCT6        │
                     │   PID @ 100 Hz · encoders · ICM-20948   │
                     └───┬───────┬───────┬───────┬─────────────┘
                        M1      M2      M3      M4
                        FL      BL      FR      BR
```

**The split matters.** Anything with a deadline — PID, encoder counting, the
2 s command timeout — lives on the STM32, where nothing can preempt it. The
host never has to be real-time, which is why a busy dashboard cannot make the
wheels stutter.

That property is what let the compute be swapped without touching the firmware.

> **The host changed on 2026-08-03.** A Raspberry Pi 5 ran this stack until it
> saturated all four cores under any real workload. It is replaced by a Beelink
> SER5 Pro — roughly 4–6× the CPU, and x86_64 rather than aarch64. The Pi's
> state is preserved on the `raspberry_pi` branch. Bring-up is not finished:
> see [[computer-setup]].
>
> The consequence for this document is narrow — the graph below is unchanged,
> because the split above held. The consequence for *tuning* is not narrow:
> every CPU-derived limit in `nav2_params.yaml`, `slam_params.yaml` and
> [[dashboard-design]] was fitted to the Pi and is now void.

## Data flowing up

| From | Topic | Rate | Note |
|---|---|---|---|
| firmware | `/odom` | on change + 0.5 s heartbeat | Raw wheel odometry, velocity-only |
| firmware | `/orbibot/encoders` | 50 Hz | `Int32MultiArray` [FL, BL, FR, BR] |
| firmware | `/imu/data_raw` | 50 Hz | 12-byte packet: gyro + accel. **No magnetometer** |
| firmware | `/imu/data` | 50 Hz | Firmware's own attitude estimate |
| firmware | `/joint_states` | 50 Hz | Wheel positions for TF |
| firmware | `/orbibot/system_status`, `/orbibot/safety_status`, `/diagnostics` | — | Battery, motor enable, faults |
| RPLidar A1 | `/scan` | 8.0 Hz | 360°, 720 pts/rev, ~8 m |
| RealSense D435 | `/camera/color/*`, `/camera/depth/*` | TBD | **Depth enabled 2026-08-03** — needs a 5000 Mbps link and the driver installed; neither is done yet |

**Depth is a new capability, not a restored one.** On the Pi the D435 sat on a
480 Mbps link with no CPU to spare, so it ran colour-only as a plain webcam.
x86_64 and 16 threads remove both limits. Nothing downstream consumes depth
yet — that is Phase 6 work in [[roadmap]].

## The estimation chain

```
/imu/data_raw ──► imu_filter_madgwick ──► /imu/data_filtered ──┐
                  (use_mag: false)                             │
                                                               ├─► EKF
/odom ─────────────────────────────────────────────────────────┘   │
                                                                   ▼
                                              /odometry/filtered
                                              TF: odom → base_footprint
```

**Heading has no absolute reference.** The magnetometer was removed on
2026-04-28 — indoors, steel, motors and battery currents distort the field
enough to make it worse than useless. Madgwick therefore runs 6-DoF, the EKF
takes IMU yaw in *relative* mode (`imu0_relative: true`, first reading becomes
zero), and yaw drift is corrected further up by slam_toolbox or AMCL through
`map → odom`.

The consequence for testing: **Phase 1 cannot prove absolute heading is
correct.** It can only bound the drift rate. Absolute heading is the map's
job — see [[roadmap]].

## TF chain

```
map → odom → base_footprint → base_link → sensor_links
```

- `map → odom` — exactly one publisher, ever: slam_toolbox **or** AMCL
- `odom → base_footprint` — the EKF
- `base_footprint → base_link` and below — URDF, `orbibot_description`

**The base frame is `base_footprint`, never `base_link`.** Consumers use
`/odometry/filtered`, not `/odom`.

## Commands flowing down

Covered in [[command-pipeline]] — including the fact that four things publish
`/cmd_vel` today and nothing arbitrates between them.

## Launch layering

Each package launches only its own nodes. Composition lives in
[[orbibot_bringup]]:

```bash
ros2 launch orbibot_bringup robot.launch.py        # description + hardware + LiDAR + EKF
ros2 launch orbibot_bringup mapping.launch.py      # + slam_toolbox
ros2 launch orbibot_bringup exploration.launch.py  # + Nav2 + frontier explorer
ros2 launch orbibot_webgui  webgui.launch.py       # rosbridge :9090, WebRTC :8081
```

## Related

[[docs/README|Docs home]] · [[command-pipeline]] · [[dashboard-design]] ·
[[computer-setup]] · [[packages-moc]] · [[rosmaster-board]] ·
[[firmware-architecture]]
