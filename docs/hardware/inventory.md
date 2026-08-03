---
title: "Hardware Inventory"
type: hardware
date: 2026-08-03
tags:
  - hardware
  - inventory
---

# Hardware Inventory

Everything physically on OrbiBot — **measured**, not copied from datasheets.
Chassis and board figures were taken on the robot on 2026-08-02; the compute
figures were taken on the Beelink on 2026-08-03, **on a bench — it is not
mounted yet**. Spare capacity is called out, because most of the roadmap in
[[roadmap]] is about using what is already here rather than buying more.

---

## Compute — Beelink SER5 Pro

Measured on the machine itself, 2026-08-03, on a bench.

| | |
|---|---|
| CPU | 8 cores / 16 threads, AMD Ryzen 7 PRO 5800H (x86_64) |
| RAM | 11.6 GiB — 1.7 used, 9.9 available at idle |
| GPU | AMD Radeon Vega (Cezanne), integrated |
| OS | Ubuntu 24.04.4 LTS **Server** — no desktop, by design |
| Storage | 457 G NVMe, 425 G free |
| Network | WiFi `wlo1` up; Gigabit Ethernet `enp1s0` present, unused |
| Firmware | SER5HU01, 2024-10-28 |

**Software installed and verified 2026-08-03** — ROS 2 Jazzy, Nav2,
slam_toolbox, rosbridge, twist-mux, RealSense, PlatformIO, Node 20; workspace
builds 12 packages in 17.9 s. See [[computer-setup]] and [[baseline-results]].

### Replacing the Raspberry Pi 5

The Pi 5 (4 × Cortex-A76, 7.8 GiB, aarch64) is being **removed from the robot
entirely**. It hit 100 % CPU under any real workload — SLAM, Nav2, the
dashboard, the camera — which made the robot uncontrollable rather than merely
slow. Its state is preserved on the `raspberry_pi` git branch.

The replacement is roughly **4–6× the CPU**, and the move from aarch64 to
x86_64 matters as much as the speed: librealsense, Nav2 and most ROS binaries
are first-class on x86_64 instead of an ARM afterthought.

**Every CPU-derived tuning number in this repo is therefore void.** The
"reduced for Raspberry Pi" comments in `nav2_params.yaml` and
`slam_params.yaml`, and the whole budget table in [[dashboard-design]], were
fitted to a machine that is no longer here. They need re-deriving from a new
baseline, not adjusting — [[roadmap]] Phase 0.

## Power conversion — RBD-2767 boost converter

New, and required: the Pi ran on 5 V from the ROSMaster board's Type-C output.
The Beelink cannot.

| | |
|---|---|
| Module | RBD-2767 — 150 W DC-DC **boost** (step-up) |
| Input | 10–32 V ← 4S LiFePO4 at 10.5–14.6 V |
| Output | 12–35 V, set by multi-turn pot → **19 V** |
| Current | 6 A rated, 10 A with cooling |
| Protection | 10 A fuse, **battery positive lead, input side** |

> The 19 V target is **confirmed**: the Beelink's adapter is labelled
> **19 V / 3.42 A (65 W)**, read 2026-08-03. The boost converter is the right
> part and the load figures below are the real ones.

Load, at ~90 % efficiency and 19 V / 65 W: **3.4 A out**, **5.6 A in** at
12.8 V, rising to **~6.9 A** as the battery sags to 10.5 V. The fuse sits on
the input side because that is the only side where 10 A is a meaningful
threshold — on the output only 3.4 A ever flows.

**Open risk:** the converter's 10 V minimum input sits 0.5 V below the BMS
cutoff at 10.5 V. Motor current transients could brown out the Beelink, and a
brown-out with the NVMe writing corrupts the filesystem. Measurements P-1…P-5
in [[computer-setup]] settle this; none have been taken.

## MCU — Yahboom ROSMaster V3.0

STM32F103RCT6, Cortex-M3 @ 72 MHz, **no FPU**. FreeRTOS, 4 tasks.

Rebuilt on the Beelink 2026-08-03, GCC 12.3.1 (`arm-none-eabi`), 89 s:

| Resource | Used | Free |
|---|---|---|
| Flash 256 KB | 24.7 KB (9.7 %) | **~231 KB** |
| RAM 48 KB | 21.6 KB (45.1 %) | ~26 KB |

The previous entry read 28.4 KB flash / 19.9 KB RAM, measured on the Pi. Flash
went **down** and RAM **up** since then — the toolchain version is the same, so
that is the firmware source changing, not the host. Nothing here depends on
which computer does the compiling; the numbers are the STM32's.

There is a lot of room for new firmware features; the binding constraint is CPU
time, not memory. See [[firmware-architecture]] and [[rosmaster-board]].

### Board peripherals

| Peripheral | Status | Notes |
|---|---|---|
| 4 × AM2857 H-bridge | **used** | 20 kHz PWM, period 3600, deadzone 1600 |
| 4 × JGB37-520 motors | **used** | 30:1 gearbox, 333 RPM no-load @ 12 V |
| 4 × quadrature encoders | **used** | 1320 CPR; **directions verified 2026-08-02** |
| ICM-20948 IMU (SPI2) | **used, 6-axis** | ±500 dps, ±2 g. The AK09916 magnetometer is on the die but **disabled** — removed 2026-04-28 |
| Battery ADC | **used** | 4S LiFePO4, divider 4.03, sampled 1 Hz |
| Buzzer (PC5) | **used** | |
| SSD1306 OLED 128×64 | **partly used** | Firmware draws it; no serial command exists (`0x41` undefined) |
| User button (PD2) | **unused** | Free digital input — a physical e-stop or mode toggle is an obvious use |
| CAN — SN65HVD230 | **unused** | Pins conflict with USB/motor; treat as unavailable |
| Servo rails 6.8 V × 4 | **unused** | Available if a pan/tilt or arm is ever added |
| RGB LED (WS2812) | **removed** | Deliberately dropped from firmware |

### Chassis

| | |
|---|---|
| Mass | ~6 kg — **with the Pi. Re-weigh after mounting the Beelink** |
| Footprint | 350 × 250 mm |
| Wheelbase (front↔rear) | 260 mm |
| Track (left↔right) | 360 mm |
| Wheels | 100 mm mecanum, ABBA layout (A = +45° rollers) |

The Beelink and its converter are heavier and bulkier than a Pi. Mass and
centre of gravity both feed traction, PID response and odometry, so **re-weigh
and re-measure the footprint after mounting** — before Phase 1 calibration, not
after. Calibrating against the old mass produces numbers that are wrong the
moment the robot is assembled.

## Sensors

| Sensor | Bus | Link speed | Topic | Rate |
|---|---|---|---|---|
| RPLidar A1 | CP2102 USB serial (`/dev/lidar`) | 12 Mbps | `/scan` | 10 Hz |
| ROSMaster board | CH340 USB serial (`/dev/motordriver`) | 12 Mbps | — | 115200 baud |
| RealSense D435 | USB | **to be re-checked** | `/camera/*` | depth + colour, target |

Nothing is plugged into the Beelink yet — `lsusb` shows only its own root hubs
and Bluetooth. The link speeds above are the Pi's; re-measure after mounting.

### The RealSense: depth is back on

On the Pi the D435 sat on a **480 Mbps (USB 2.0)** link with no CPU to spare,
so depth was switched off and the camera was demoted to a plain webcam. Both
halves of that constraint are gone: x86_64 has first-class librealsense, and
there are 16 threads instead of 4.

**Full depth is enabled going forward** (decision, 2026-08-03). It needs a real
USB 3 link:

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/product" ] && echo "$(cat $d/product) — $(cat $d/speed) Mbps"
done | grep -i realsense
```

Until that reads **5000**, depth and colour cannot run together at useful
resolution and the driver will silently drop stream combinations. Blue port,
USB 3-rated cable.

## Missing software the hardware implies

Installed 2026-08-03 by `scripts/setup_computer.sh`. What matters beyond the
obvious:

| Package | State | Consequence |
|---|---|---|
| ROS 2 Jazzy + `ros-dev-tools` | **installed** | |
| `ros-jazzy-twist-mux` | **installed** | Closes the gap that existed for the Pi's whole life — four `/cmd_vel` publishers with nothing arbitrating. Configuring it is Phase 2, see [[command-pipeline]] |
| `ros-jazzy-realsense2-camera` | **installed** | Depth is enabled by decision; on the Pi this driver was deliberately bypassed |
| `python3-anthropic`, `python3-mcp` | **pip, not apt** | No apt candidate on 24.04. Installed with `pip --user`; see `orbibot_agent/agent-issues.md` |
| `ros-jazzy-joy` | not installed — **not needed** | `orbibot_teleop` declares it and subscribes to `/joy`, so that package is dormant. Teleop is web-only by decision; leave it uninstalled |
| `ros-jazzy-foxglove-bridge` | not installed | Optional; relevant to [[dashboard-design]] |

All are available in apt for Jazzy on noble/x86_64.

## Spare capacity worth using

- **~228 KB MCU flash, ~29 KB RAM** — room for host-testable modules, richer
  diagnostics, stack monitoring
- **PD2 user button** — a hardware e-stop or mode switch with no new parts
- **12 threads of CPU that were never available before** — the Pi ran out at
  four. Depth perception, a real dashboard, MPPI at a sane batch size and
  agentic workloads all become affordable at once. The risk now is the
  opposite of the Pi's: config files that still throttle themselves for
  hardware that is gone
- **425 G of NVMe** — bag recording stops being rationed. On a 58 G SD card it
  effectively was
- **Gigabit Ethernet, unused** — a wired link for map transfers or a tethered
  debugging session, without competing with the teleop path on WiFi
- **Radeon Vega iGPU** — unused. Makes headless simulation and any future
  vision model genuinely viable, unlike VideoCore VII

## Related

[[rosmaster-board]] · [[components]] · [[computer-setup]] · [[roadmap]] ·
[[backlog-moc]]
