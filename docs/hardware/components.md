---
title: "Component Specifications"
type: hardware
tags:
  - hardware
  - components
---

# OrbiBot Component Specifications

## 1. Core Computing Platform

### Beelink SER5 Pro

Replaced the Raspberry Pi 5 on 2026-08-03. Values marked *measured* were read
off this machine; the rest are vendor specification and should be confirmed.

| Specification | Value | Source |
|--------------|-------|--------|
| CPU | AMD Ryzen 7 PRO 5800H — 8 cores / 16 threads | measured |
| Architecture | x86_64 | measured |
| RAM | 11.6 GiB usable (some carved out for the iGPU) | measured |
| GPU | AMD Radeon Vega (Cezanne), integrated | measured |
| Storage | 457 GB NVMe SSD, 425 GB free | measured |
| OS | Ubuntu 24.04.4 LTS Server | measured |
| BIOS | SER5HU01, 2024-10-28 | measured |
| Input Voltage | **19V DC — verify against the adapter label** | assumed |
| Power Consumption | ~15W idle, ~65W peak | assumed |

#### Connectivity & I/O
- **Wireless:** Intel AX200 — WiFi 6 + Bluetooth 5.2 *(BT controller measured)*
- **Wired:** Gigabit Ethernet (`enp1s0`, present and unused)
- **USB Ports:** USB 3.2 and USB 2.0; two USB 3.0 root hubs seen by `lsusb`
- **Display:** HDMI + DisplayPort *(unused — headless server)*

#### Why it replaced the Pi 5

The Pi 5 saturated all four cores under any real workload — SLAM, Nav2, the
dashboard or the camera — which made the robot uncontrollable, not just slow.

| | Pi 5 | Beelink SER5 Pro |
|---|---|---|
| Cores / threads | 4 / 4 | 8 / 16 |
| Architecture | aarch64 | x86_64 |
| RAM | 7.8 GiB | 11.6 GiB |
| Storage | 58 GB SD card | 457 GB NVMe |
| Powered from | 5V, ROSMaster Type-C | 19V via DC-DC boost |

The architecture change matters as much as the core count: on x86_64,
librealsense, Nav2 and most ROS 2 binaries are first-class rather than an ARM
afterthought. This is what makes RealSense depth viable — see [[inventory]].

**Cost:** roughly 20–25W more draw, and the ROSMaster board can no longer power
the computer. Both are addressed in §5.

---

## 2. Motor Control System

### Yahboom ROS Robot Control Board V3.0

| Specification | Value |
|--------------|-------|
| Model | Yahboom ROS Robot Control Board V3.0 |
| MCU | STM32F103RCT6 (ARM Cortex-M3) |
| Flash Memory | 256KB |
| SRAM | 48KB |
| Input Voltage | 12V DC (9-16V range) |
| Output Voltage | 5.1V/5A (Type-C) — **unused since the Pi was removed** |
| Motor Channels | 4-channel with encoder support |
| Maximum Current | 10A total (5A per channel) |
| Board Power | 3-5W |
| Weight | ~80g |

#### Integrated Sensors
- **IMU:** 9-axis sensor (3-axis gyroscope, accelerometer, magnetometer)
- **Resolution:** 16-bit ADC
- **Update Rate:** Up to 1kHz

#### Control Features
- PID motor speed control
- Encoder feedback processing
- PWM servo control (4 channels)
- Reverse-polarity protection
- Short-circuit protection
- Over-current protection

#### Communication Interfaces
- **Primary:** USB Serial to the host computer (`/dev/motordriver`, 115200 baud)
- **Secondary:** CAN bus
- **RC Control:** SBUS receiver support
- **GPIO:** 51 programmable I/O pins

---

## 3. Drive System

### Motors: Yahboom JGB37-520 DC Geared Motor with Encoder (Qty: 4)

| Specification | Value |
|--------------|-------|
| Model | JGB37-520 DC Motor |
| Rated Voltage | 12V DC |
| Rated Current | 0.3A per motor |
| Stall Current | 3A per motor |
| Rated Power | 3.6W per motor |
| Speed | 333 RPM ± 10 RPM |
| Gear Ratio | 1:30 reduction |
| Rated Torque | 3.3 kg·cm |
| Stall Torque | 4.8 kg·cm |
| Output Shaft | 6mm D-type |
| Weight | 150g per motor |
| Dimensions | 37 × 20 × 20mm |

#### Encoder Specifications
- **Type:** Hall sensor encoder
- **Resolution:** 11 PPR (Pulses Per Revolution)
- **Output:** A/B phase incremental
- **Counts per Revolution:** 1,320 (after gear reduction)
- **Voltage:** 3.3V - 5V
- **Features:** Built-in shaping and pull-up resistors

### Wheels: 100mm Steel Mecanum Wheels (Qty: 4)

| Specification | Value |
|--------------|-------|
| Diameter | 100mm |
| Width | 50mm |
| Roller Length | 19mm |
| Weight | 400g per wheel |
| Load Capacity | 15kg per wheel (60kg total) |
| Material | Steel construction |
| Bearing Type | Sealed ball bearings |
| Roller Angle | 45° |

#### Performance Calculations
- **Wheel Circumference:** π × 100mm = 314.16mm
- **Theoretical Max Speed:** 1.74 m/s
- **Recommended Max Speed:** 1.0 m/s (for stability)
- **Minimum Turn Radius:** 0m (point rotation)

---

## 4. Sensor Systems

### LIDAR: RPLIDAR A1 - 2D Laser Scanner

| Specification | Value |
|--------------|-------|
| Model | RPLIDAR A1 |
| Scan Range | 0.15 - 12 meters |
| Scan Rate | 5.5 Hz (configurable up to 10 Hz) |
| Angular Resolution | ≤1° |
| Points per Rotation | Up to 1,450 |
| Accuracy | ±1% - 2.5% (distance dependent) |
| Operating Voltage | 5V (4.9V - 5.5V) |
| Motor Voltage | 5V (up to 9V permissible) |
| Power Consumption | 0.5W |
| Weight | ~190g |
| Dimensions | 98.5 × 70 × 41mm |

#### Communication
- **Interface:** UART
- **Baud Rate:** 115,200 bps
- **Protocol:** Proprietary RPLIDAR protocol
- **Data Output:** Distance, angle, quality

### Depth Camera: Intel RealSense D435

| Specification | Value |
|--------------|-------|
| Model | Intel RealSense D435 |
| Technology | Active IR stereo |
| Depth Resolution | Up to 1280×720 |
| RGB Resolution | 1920×1080 |
| Frame Rate | 30 fps (depth), 60 fps (RGB) |
| Depth Range | 0.1 - 10+ meters |
| Depth Accuracy | <2% at 2m |
| Field of View | 87° × 58° (depth), 69° × 42° (RGB) |
| Interface | USB 3.0 |
| Power Consumption | 1.5W - 3W |
| Weight | ~175g |
| Dimensions | 90 × 25 × 25mm |

#### Capabilities
- Real-time depth mapping
- 3D point cloud generation
- Object detection and tracking
- Visual odometry
- SLAM (Simultaneous Localization and Mapping)

---

## 5. Power System

### Battery Pack: 4S 12.8V 15Ah LiFePO4

| Specification | Value | Notes |
|--------------|-------|-------|
| Chemistry | LiFePO₄ (Lithium Iron Phosphate) | Highly stable, long cycle life |
| Configuration | 4S (4 cells in series) | Provides 12.8V nominal voltage |
| Nominal Voltage | 12.8V | Operating voltage |
| Full Charge Voltage | 14.6V | Cutoff voltage for charging (3.65V/cell) |
| Cut-off Voltage | 10.0V | BMS low voltage protection (2.5V/cell) |
| Pack Capacity | 15.5Ah (15,500mAh) | Total charge capacity |
| Total Energy | 198.4Wh | Energy stored (12.8V × 15.5Ah) |
| Max Continuous Discharge | 100A (BMS limit) | Maximum safe current draw |
| Pack Weight | 1.3kg | Lightweight for the capacity |
| Cycle Life | 3,000+ cycles | To 80% original capacity |
| Safe Temp. (Discharge) | -20°C to 60°C | Wide operating range |

### Individual Cell Specifications

| Characteristic | Value | Notes |
|---------------|-------|-------|
| Cell Model | IFR-32140 | Cylindrical LiFePO₄ |
| Nominal Voltage | 3.2V | Single cell voltage |
| Cell Capacity | 15.5Ah | Capacity per cell |
| Max Continuous Current | 45A | Per cell rating (limited by pack/BMS) |
| Peak Discharge Current | 75A | 3 seconds burst rating |
| Max Charge Current | 15A (1C rate) | Maximum current for fastest charge |
| Standard Charge Current | 3A (0.2C rate) | Recommended charge current for longevity |
| Cell Weight | 300g | Individual cell weight |

### Battery Management System (BMS)

| Feature | Specification | Purpose |
|---------|--------------|---------|
| Model Type | 4S 100A LiFePO₄ BMS with Balance | Ensures safe operation and longevity |
| Discharge Rating | 100A continuous | Max current before BMS cutoff |
| Charge Current Max | 8A | Limits charger current to protect cells/BMS |
| Charging Voltage | 15V (14.6V typical) | Input voltage requirement |
| Balance Function | Active cell balancing | Maintains voltage equality among cells |
| Overcharge Protection | Cuts off at 15V | Prevents cell damage from over-voltage |
| Over-discharge Protection | Cuts off at 10V | Prevents deep discharge damage |
| Over-current Protection | Limits to 100A | Protects against excessive load current |
| Short Circuit Protection | Instant cutoff | Immediate response to short circuit |
| Temperature Protection | Auto thermal monitoring | Prevents thermal runaway |
| Reverse Polarity | Included | Protection from incorrect wiring |

### DC-DC Boost Converter: RBD-2767

Added 2026-08-03. The Pi 5 ran on 5V from the ROSMaster board's Type-C output;
the Beelink needs ~19V at up to 65W, which no existing rail provides.

| Specification | Value |
|--------------|-------|
| Type | Step-up (boost) — output must exceed input |
| Rated Power | 150W |
| Input Range | 10–32V DC |
| Output Range | 12–35V DC, adjustable via multi-turn potentiometer |
| Output Current | 6A continuous, 10A peak with cooling |
| Cooling | Dual heatsinks, toroidal inductor |
| Terminals | Screw terminals, LED power indicator |

#### Operating point

| | Value |
|---|---|
| Input | 12.8V nominal (10.5V BMS cutoff – 14.6V full charge) |
| Output | **19V — pending confirmation against the adapter label** |
| Output current | ~3.4A (65W ÷ 19V) — 57% of the 6A rating |
| Input current | ~5.6A at 12.8V; ~6.9A at 10.5V |
| Efficiency assumed | ~90% |

#### Protection

**10A fuse, slow-blow, in the battery positive lead on the input side.** The
input carries 5.6–6.9A, so 10A is a meaningful threshold there. On the output
side only 3.4A ever flows and a 10A fuse would never blow.

⚠️ **The output voltage must be set with a multimeter before the Beelink is
connected.** The multi-turn pot ships at an arbitrary position and its range
reaches 35V.

⚠️ **Margin warning:** the converter's 10V minimum input is only 0.5V below the
BMS cutoff at 10.5V. Motor transients could brown out the Beelink, and a
brown-out during an NVMe write corrupts the filesystem. Measurements P-1…P-5
in [[beelink-bringup]] settle this. None have been taken.

### Power Distribution

```
4S LiFePO4 12.8V ──┬── 10A fuse ── RBD-2767 boost ── 19V ── Beelink SER5 Pro
   198.4 Wh        │
                   └── ROSMaster V3.0 board ──┬── 4× JGB37-520 motors
                                              ├── 5V rail ── RPLidar A1
                                              └── STM32 + ICM-20948
```

The RealSense D435 draws its 1.5–3W from the Beelink's USB 3 port.

#### Energy budget — estimates, not measured

| State | Estimated draw | Estimated runtime on 198.4Wh |
|---|---|---|
| Idle, stack up, not driving | ~30W | ~6.5h |
| Driving with Nav2 + SLAM + dashboard | ~85W | ~2.3h |

The Beelink costs roughly 20–25W more than the Pi did. Plan sessions around
~2h of active driving until these are replaced with measurements.

---

## 6. Mechanical Specifications

### Chassis

| Specification | Value |
|--------------|-------|
| Material | Aluminum extrusion or steel frame |
| Dimensions | ~400 × 300 × 200mm (L×W×H) |
| Weight | 800g (estimated) |
| Mounting | Standard hole patterns |

### Robot Dimensions

- **Length:** 14 inch (355.6mm)
- **Width:** 10 inch (254mm)
- **Height:** 4 inch (101.6mm)
- **LIDAR Height:** 6 inch (152.4mm)

> ⚠️ **Stale as of 2026-08-03.** These figures, and the ~6kg total mass in
> [[inventory]], were measured with the Raspberry Pi 5 fitted. The Beelink and
> its boost converter are heavier and bulkier. Mass and centre of gravity feed
> traction, PID response and odometry directly, so **re-weigh and re-measure
> after mounting and before Phase 1 calibration** — see [[roadmap]].

---

## Related

[[inventory]] · [[rosmaster-board]] · [[beelink-bringup]] · [[roadmap]]
