# OrbiBot Component Specifications

## 1. Core Computing Platform

### Raspberry Pi 5 (8GB RAM)

| Specification | Value |
|--------------|-------|
| Model | Raspberry Pi 5 - 8GB RAM |
| CPU | 2.4GHz Quad-core 64-bit ARM Cortex-A76 |
| RAM | 8GB LPDDR4X-4267 |
| GPU | VideoCore VII (OpenGL ES 3.1, Vulkan 1.2) |
| Input Voltage | 5V DC |
| Power Consumption | 15-27W (typical 15-20W) |
| Maximum Current | 5A |
| Weight | 45g |
| Dimensions | 85 × 56 × 17mm |

#### Connectivity & I/O
- **Wireless:** Dual-band 802.11ac Wi-Fi, Bluetooth 5.0/BLE
- **Wired:** Gigabit Ethernet
- **USB Ports:** 2× USB 3.0, 2× USB 2.0
- **GPIO:** 40-pin header (26 GPIO pins)
- **Camera:** 2× MIPI CSI connectors
- **Display:** 2× MIPI DSI connectors
- **Expansion:** PCIe 2.0 x1 interface

#### Key Features
- Dual 4K display output with HDR support
- Real-time clock with battery backup
- Power Delivery support via USB-C
- Hardware video encode/decode
- Secure boot capability

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
| Output Voltage | 5.1V/5A (Type-C to Raspberry Pi) |
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
- **Primary:** USB Serial (to Raspberry Pi)
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
