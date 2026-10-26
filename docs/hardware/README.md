---
title: "Hardware Inventory"
type: hardware
date: 2026-08-02
tags:
  - hardware
  - inventory
---

# Hardware Inventory

Everything physically on OrbiBot, **measured on the robot** on 2026-08-02 —
not copied from datasheets. Spare capacity is called out, because most of the
roadmap in [[roadmap]] is about using what is already here rather than buying
more.

---

## Compute — Raspberry Pi 5 Model B Rev 1.0

| | |
|---|---|
| CPU | 4 × Cortex-A76 @ 2.4 GHz (aarch64) |
| RAM | 7.8 GiB — 1.7 used, 6.1 available at idle |
| OS | Ubuntu 24.04.4 LTS, ROS 2 Jazzy |
| Storage | 58 G card, 43 G free |
| Thermals | 49.4 °C idle, `throttled=0x0` — no throttling seen |
| Load | 0.01 idle |

The Pi 5 is a large step up from the Pi 4 this stack's tuning was written for.
Several "reduced for Raspberry Pi" settings in `nav2_params.yaml` are likely
now over-conservative — see [[roadmap]] Phase 6.

## MCU — Yahboom ROSMaster V3.0

STM32F103RCT6, Cortex-M3 @ 72 MHz, **no FPU**. FreeRTOS, 4 tasks.

| Resource | Used | Free |
|---|---|---|
| Flash 256 KB | 28.4 KB (10.9 %) | **~228 KB** |
| RAM 48 KB | 19.9 KB (40.4 %) | ~29 KB |

Measured with GCC 12.3 on the Pi. There is a lot of room for new firmware
features; the binding constraint is CPU time, not memory. See
[[firmware-architecture]] and [[rosmaster-board]].

### Board peripherals

| Peripheral | Status | Notes |
|---|---|---|
| 4 × AM2857 H-bridge | **used** | 20 kHz PWM, period 3600, deadzone 1600 |
| 4 × JGB37-520 motors | **used** | 30:1 gearbox, 333 RPM no-load @ 12 V |
| 4 × quadrature encoders | **used** | 1320 CPR; **directions verified 2026-08-02** |
| ICM-20948 IMU (SPI2) | **used** | ±500 dps, ±2 g, AK09916 magnetometer |
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
| Mass | ~6 kg |
| Footprint | 350 × 250 mm |
| Wheelbase (front↔rear) | 260 mm |
| Track (left↔right) | 360 mm |
| Wheels | 100 mm mecanum, ABBA layout (A = +45° rollers) |

## Sensors

| Sensor | Bus | Link speed | Topic | Rate |
|---|---|---|---|---|
| RPLidar A1 | CP2102 USB serial (`/dev/lidar`) | 12 Mbps | `/scan` | 10 Hz |
| ROSMaster board | CH340 USB serial (`/dev/motordriver`) | 12 Mbps | — | 115200 baud |
| RealSense D435 | USB | **480 Mbps ⚠️** | `/camera/*` | 15 Hz configured |

### ⚠️ The RealSense is on a USB 2.0 link

Measured: `Intel(R) RealSense(TM) Depth Camera 435 — 480 Mbps`. The Pi 5 has
**two idle 5000 Mbps controllers**. At 480 Mbps the D435 cannot deliver depth
and colour at useful resolution simultaneously, and the driver will silently
drop or refuse stream combinations.

**Fix**: move the camera to a blue (USB 3) port and use a USB 3-rated cable.
Re-check with:

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/product" ] && echo "$(cat $d/product) — $(cat $d/speed) Mbps"
done | grep -i realsense
```

Until that reads 5000, treat any depth-camera work as blocked.

## Missing software the hardware implies

| Package | State | Consequence |
|---|---|---|
| `ros-jazzy-twist-mux` | **not installed — needed** | No arbitration between the four `/cmd_vel` publishers — see [[command-pipeline]] |
| `ros-jazzy-joy` | not installed — **not needed** | `orbibot_teleop` declares it and subscribes to `/joy`, so that package is dormant. Teleop is web-only by decision; leave it uninstalled |
| `ros-jazzy-foxglove-bridge` | not installed | Optional; relevant to [[dashboard-design]] |

All are available in apt for this distro.

## Spare capacity worth using

- **~228 KB MCU flash, ~29 KB RAM** — room for host-testable modules, richer
  diagnostics, stack monitoring
- **Two idle USB 3 controllers** — the camera belongs on one
- **PD2 user button** — a hardware e-stop or mode switch with no new parts
- **Pi 5 headroom** — idle at 0.01 load and 49 °C; the Nav2 tuning inherited
  from Pi 4 assumptions is worth re-measuring rather than trusted

## Related

[[rosmaster-board]] · [[components]] · [[roadmap]] · [[backlog-moc]]
