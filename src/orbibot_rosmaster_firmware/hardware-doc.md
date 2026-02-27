# OrbiBot Hardware Documentation

Complete hardware specifications for the Yahboom ROSMaster V3.0 Expansion Board used in OrbiBot.

---

## Board Overview

**Target Board**: Yahboom ROSMaster V3.0 Expansion Board
**MCU**: STM32F103RCT6 (ARM Cortex-M3)
**Clock Speed**: 72 MHz
**Flash Memory**: 256 KB
**SRAM**: 48 KB
**Logic Voltage**: 3.3V
**Programming**: USB bootloader (BOOT0 pin), SWD debug interface

---

## Motor PWM Configuration

### Motor Driver Hardware
- **Driver IC**: AM2857 × 4 (dual H-bridge per motor)
- **Motor Supply**: VM rail (12V nominal from 4S LiFePO4)
- **PWM Frequency**: 20 kHz
- **PWM Period**: 3600 counts (0-3600 range)
- **Deadzone Offset**: 1600 (minimum PWM for motion)

### Motor Pin Mappings

| Motor | Position | Timer | PWM_A Pin | PWM_B Pin | CCR Registers |
|-------|----------|-------|-----------|-----------|---------------|
| M1 | Front-Left | TIM8 | PA11 | PA8 | CCR1 / CCR2 |
| M2 | Back-Left | TIM8 | PB0 | PB1 | CCR3 / CCR4 |
| M3 | Front-Right | TIM1 | PC6 | PC7 | CCR4 / CCR1 |
| M4 | Back-Right | TIM1 | PC8 | PC9 | CCR2 / CCR3 |

**Important Notes:**
- TIM1 requires `GPIO_PartialRemap_TIM1` to map channels to Port C
- M2 uses PB0/PB1 (not PA9/PA10 as shown in schematic) to avoid USART1 conflict
- PA11 is shared with USB_DM (mutually exclusive - USB only for programming)

### Timer Configuration
```c
Prescaler: 0 (72 MHz / 1 = 72 MHz timer clock)
Period: 3600 - 1
PWM Frequency: 72 MHz / 3600 = 20 kHz
Mode: PWM Mode 1 (active high)
```

### Deadzone Compensation
Motors require minimum PWM to overcome static friction:
```c
if (speed > 0) output = speed + 1600;
if (speed < 0) output = speed - 1600;
```

---

## Encoder Configuration

### Encoder Hardware
- **Type**: Quadrature Hall effect encoders (3.3V logic)
- **Resolution**: 1320 CPR (Counts Per Revolution)
  - Base encoder: 11 PPR
  - Gear ratio: 30:1
  - Quadrature: 4× multiplier
  - Total: 11 × 30 × 4 = 1320 CPR
- **Filter**: 10-sample digital filter (TIM_ICFilter)

### Encoder Pin Mappings

| Motor | Timer | Encoder A | Encoder B | Remap Required |
|-------|-------|-----------|-----------|----------------|
| M1 | TIM2 | PA15 | PB3 | Yes (JTAG disable) |
| M2 | TIM4 | PB6 | PB7 | No |
| M3 | TIM5 | PA0 | PA1 | No |
| M4 | TIM3 | PA6 | PA7 | No |

**CRITICAL - TIM2 Remapping:**
- PA15 and PB3 are JTAG pins by default
- Must disable JTAG and enable SWD-only mode
- Register: `AFIO->MAPR` bit SWJ_CFG[2:0] = 0b010 (SWD enable, JTAG disable)
- After reset, PA15/PB3 become available as TIM2 CH1/CH2 (partial remap)

### Timer Encoder Mode Configuration
```c
Mode: TIM_EncoderMode_TI12 (count on both edges of both channels)
Counter: 16-bit (0x0000 - 0xFFFF)
Initialization: 0x7FFF (midpoint for bidirectional counting)
Polarity: TIM_ICPolarity_Rising (both channels)
Filter: TIM_ICFILTER_10 (noise rejection)
```

---

## IMU Configuration (ICM-20948)

### IMU Hardware
- **Sensor**: ICM-20948 9-axis IMU (primary on V3.0 board)
- **Legacy Support**: MPU-9250 via I2C (older boards)
- **Interface**: SPI2 (preferred), I2C fallback
- **Voltage**: 3.3V
- **Update Rate**: 50 Hz (task_imu)

### ICM-20948 Specifications
- **Accelerometer**: ±2g, ±4g, ±8g, ±16g (±16g default)
- **Gyroscope**: ±250, ±500, ±1000, ±2000 dps (±2000 dps default)
- **Magnetometer**: AK09916 (auxiliary I2C, ±4900 µT)
- **FIFO**: 512 bytes
- **Bank Switching**: 4 register banks (0-3) via REG_BANK_SEL

### SPI2 Pin Mappings

| Signal | Pin | Function |
|--------|-----|----------|
| CS (NSS) | PB12 | Chip select (active low) |
| SCK | PB13 | Serial clock |
| MISO | PB14 | Master in, slave out |
| MOSI | PB15 | Master out, slave in |

**SPI Configuration:**
```c
Mode: SPI_Mode_Master
Direction: SPI_Direction_2Lines_FullDuplex
DataSize: SPI_DataSize_8b
CPOL: SPI_CPOL_High (idle high)
CPHA: SPI_CPHA_2Edge (sample on rising edge)
BaudRate: SPI_BaudRatePrescaler_16 (72MHz/16 = 4.5MHz)
FirstBit: SPI_FirstBit_MSB
```

### Important Register Access
- **WHO_AM_I** (Bank 0, 0x00): Should return 0xEA for ICM-20948
- **Bank Selection** (0x7F): Switch between register banks
- **Read Operation**: Set bit 7 high (0x80 | address)
- **Write Operation**: Address as-is

---

## Serial Communication (USART1)

### USART Configuration
- **Pins**: TX = PA9, RX = PA10
- **Baud Rate**: 115200
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None
- **DMA**: Enabled for TX (reduces CPU load)

### Serial Protocol

**Packet Structure:**
```
[Header] [Device_ID] [Length] [Function] [Data...] [Checksum]
  0xFF      1 byte    1 byte    1 byte     N bytes    1 byte
```

**Device IDs:**
- Receive (MCU as target): `0xFC`
- Transmit (MCU as source): `0xFB`

**Checksum Calculation:**
```c
checksum = Device_ID ^ Length ^ Function ^ Data[0] ^ Data[1] ^ ... ^ Data[N-1]
```

**Key Function Codes:**
| Code | Name | Direction | Description |
|------|------|-----------|-------------|
| 0x01 | AUTO_REPORT | RX | Enable/disable auto-reporting |
| 0x0A | REPORT_SPEED | TX | Motion speed (Vx, Vy, Vz) + battery |
| 0x0C | REPORT_IMU_ATT | TX | IMU attitude (roll, pitch, yaw) |
| 0x0D | REPORT_ENCODER | TX | Encoder counts (4 motors) |
| 0x0E | REPORT_ICM_RAW | TX | Raw gyro/accel data |
| 0x12 | MOTION | RX | 3D velocity command (Vx, Vy, Vz) |

---

## Other Peripherals

### Buzzer
- **Pin**: PC5
- **Type**: Active buzzer (5V)
- **Driver**: SS8050 NPN transistor (logic level control)
- **Control**: GPIO output (high = on, low = off)

### User Button
- **Pin**: PD2
- **Type**: Tactile switch
- **Active Level**: Low (pull-up resistor)
- **Function**: User input / firmware trigger

### OLED Display
- **Interface**: I2C1
- **Address**: 0x3C (7-bit)
- **Controller**: SSD1306
- **Resolution**: 128×64 pixels
- **Voltage**: 5V (with onboard regulator)

### CAN Bus
- **Transceiver**: SN65HVD230
- **Pins**: CAN_RX (PA11), CAN_TX (PA12)
- **Termination**: 120Ω onboard
- **Status**: Available for future expansion (not implemented in current firmware)

### USB Interface
- **Controller**: CH340N (USB-to-Serial)
- **Connector**: USB Type-C
- **Pins**: USB_DM (PA11), USB_DP (PA12)
- **Usage**: Firmware upload and serial debugging

---

## Power Rails

| Rail | Voltage | Source | Usage |
|------|---------|--------|-------|
| VM | 12V nominal | 4S LiFePO4 battery | Motor drivers |
| VCC_SERVO | 6.8V | DC-DC buck converter | Servo motors (if used) |
| VCC_5V | 5V | DC-DC buck converter | USB, buzzer, OLED |
| VCC_3V3 | 3.3V | LDO regulator | MCU, IMU, encoders |

### Battery Specifications (OrbiBot)
- **Type**: 4S LiFePO4 (Lithium Iron Phosphate)
- **Nominal Voltage**: 12.8V (3.2V per cell)
- **Fully Charged**: 14.6V (3.65V per cell)
- **Low Voltage Warning**: 11.0V (2.75V per cell)
- **Critical Cutoff**: 10.5V (2.625V per cell)

---

## Robot Mechanical Configuration

### Mecanum Wheel Layout (ABBA Pattern)
```
Front-Left (A)  ╲   ╱  Front-Right (B)
                 ╲ ╱
                 ╱ ╲
Back-Left  (B)  ╱   ╲  Back-Right  (A)
```

**Wheel Types:**
- **A-type**: Rollers at +45° (FL, RR)
- **B-type**: Rollers at -45° (FR, RL)

### Physical Dimensions
- **Wheelbase** (front-to-rear): 260 mm (130 mm half-wheelbase)
- **Track Width** (left-to-right): 360 mm (180 mm half-track)
- **Wheel Radius**: 50 mm (100 mm diameter mecanum wheels)
- **Wheel Type**: 100mm mecanum wheels with 40mm rubber rollers

### Motor Specifications
- **Model**: JGB37-520 DC geared motor
- **Gear Ratio**: 30:1
- **No-Load Speed**: 333 RPM @ 12V
- **Encoder**: 11 PPR Hall effect (1320 CPR after gearing and quadrature)

---

## Control Parameters

### PID Control (Incremental Algorithm)
**Default Tuning Values** (100 Hz update rate):
- **Kp** (Proportional): 0.8
- **Ki** (Integral): 0.06
- **Kd** (Derivative): 0.5

**Incremental PID Formula:**
```
ΔOut = Kp × (Ek - Ek-1) + Ki × Ek + Kd × (Ek - 2×Ek-1 + Ek-2)
Out_k = Out_k-1 + ΔOut
```

**Anti-Windup**: Output saturated at ±3600 (max PWM)

### Mecanum Kinematics

**Inverse Kinematics** (Robot velocity → Wheel speeds):
```
ωFL = (Vx - Vy - (lx + ly) × ω) / r
ωFR = (Vx + Vy + (lx + ly) × ω) / r
ωRL = (Vx + Vy - (lx + ly) × ω) / r
ωRR = (Vx - Vy + (lx + ly) × ω) / r

Where:
- Vx, Vy = linear velocity (m/s)
- ω = angular velocity (rad/s)
- r = wheel radius (0.05 m)
- lx = half wheelbase (0.13 m)
- ly = half track width (0.18 m)
```

**Forward Kinematics** (Wheel speeds → Robot velocity):
```
Vx = (ωFL + ωFR + ωRL + ωRR) × r / 4
Vy = (-ωFL + ωFR + ωRL - ωRR) × r / 4
ω  = (-ωFL + ωFR - ωRL + ωRR) × r / (4 × (lx + ly))
```

---

## FreeRTOS Task Architecture

| Task Name | Priority | Rate | Stack Size | Function |
|-----------|----------|------|------------|----------|
| task_control | 10 (highest) | 100 Hz | 256 words | Motor PID control loop |
| task_communication | 9 | Async | 512 words | Serial RX/TX processing |
| task_imu | 8 | 50 Hz | 256 words | IMU data acquisition |
| task_monitoring | 5 | 10 Hz | 128 words | Battery, diagnostics, safety |

**Heap Configuration**: 20 KB FreeRTOS heap

---

## GPIO Port Summary

### Port A
| Pin | Function | Type | Notes |
|-----|----------|------|-------|
| PA0 | TIM5_CH1 (M3 Enc A) | Input | Encoder |
| PA1 | TIM5_CH2 (M3 Enc B) | Input | Encoder |
| PA6 | TIM3_CH1 (M4 Enc A) | Input | Encoder |
| PA7 | TIM3_CH2 (M4 Enc B) | Input | Encoder |
| PA8 | TIM8_CH2 (M1 PWM B) | AF_PP | Motor PWM |
| PA9 | USART1_TX | AF_PP | Serial TX |
| PA10 | USART1_RX | Input | Serial RX |
| PA11 | TIM8_CH1 (M1 PWM A) / USB_DM | AF_PP | Shared (mutually exclusive) |
| PA12 | USB_DP | - | USB programming |
| PA13 | SWDIO | - | SWD debug |
| PA14 | SWCLK | - | SWD debug |
| PA15 | TIM2_CH1 (M1 Enc A) | Input | JTAG remapped |

### Port B
| Pin | Function | Type | Notes |
|-----|----------|------|-------|
| PB0 | TIM8_CH3 (M2 PWM A) | AF_PP | Motor PWM |
| PB1 | TIM8_CH4 (M2 PWM B) | AF_PP | Motor PWM |
| PB3 | TIM2_CH2 (M1 Enc B) | Input | JTAG remapped |
| PB6 | TIM4_CH1 (M2 Enc A) | Input | Encoder |
| PB7 | TIM4_CH2 (M2 Enc B) | Input | Encoder |
| PB12 | SPI2_NSS (IMU CS) | Output | IMU chip select |
| PB13 | SPI2_SCK | AF_PP | IMU SPI clock |
| PB14 | SPI2_MISO | Input | IMU SPI data in |
| PB15 | SPI2_MOSI | AF_PP | IMU SPI data out |

### Port C
| Pin | Function | Type | Notes |
|-----|----------|------|-------|
| PC5 | Buzzer | Output | Active buzzer control |
| PC6 | TIM1_CH4 (M3 PWM A) | AF_PP | Motor PWM (partial remap) |
| PC7 | TIM1_CH1 (M3 PWM B) | AF_PP | Motor PWM (partial remap) |
| PC8 | TIM1_CH2 (M4 PWM A) | AF_PP | Motor PWM (partial remap) |
| PC9 | TIM1_CH3 (M4 PWM B) | AF_PP | Motor PWM (partial remap) |

### Port D
| Pin | Function | Type | Notes |
|-----|----------|------|-------|
| PD2 | KEY1 (User button) | Input | Pull-up, active low |

---

## Pin Conflict Notes

### Shared Resources
1. **PA11**: TIM8_CH1 (M1 PWM) vs USB_DM
   - USB only active during programming (BOOT0 mode)
   - No conflict during normal operation

2. **PA15/PB3**: TIM2 encoder vs JTAG
   - JTAG disabled in firmware (SWD-only mode)
   - SWD debugging still functional via PA13/PA14

3. **M2 Motor Pins**: Schematic shows PA9/PA10, firmware uses PB0/PB1
   - **Actual implementation**: PB0/PB1 (avoids USART1 conflict)
   - Verified from working firmware code

---

## Memory Map

### Flash Layout (256 KB total)
- **Bootloader**: 0x0800 0000 - 0x0800 3FFF (16 KB, protected)
- **Firmware**: 0x0800 4000 - 0x0803 FFFF (240 KB)
- **Current Usage**: ~15.5 KB (5.9%)

### RAM Layout (48 KB total)
- **FreeRTOS Heap**: 20 KB
- **Task Stacks**: ~4 KB (4 tasks)
- **Global Variables**: ~2 KB
- **System Stack**: 2 KB
- **Current Usage**: ~18.2 KB (37%)

---

## Timing Specifications

### Critical Timing Constraints
- **Motor PWM**: 20 kHz (50 µs period)
- **PID Control Loop**: 100 Hz (10 ms period)
- **IMU Sampling**: 50 Hz (20 ms period)
- **Serial Protocol**: 115200 baud (~8.68 µs per bit)
- **Command Timeout**: 2000 ms (safety stop if no command)

---

## References

### Original Hardware Documentation
- **Yahboom GitHub**: https://github.com/YahboomTechnology/ROS-robot-expansion-board
- **Board Schematics & Orginial Firmware**: [Yahboom Drive Link](https://drive.google.com/drive/folders/1ZZzCAvHwwE58BqAyxomG6oFLv9xpmeW2?usp=drive_link)


### Datasheets
- STM32F103RCT6: [STM32F103xC Datasheet](https://www.st.com/resource/en/datasheet/stm32f103rc.pdf)
- ICM-20948: [9-Axis IMU Datasheet](https://invensense.tdk.com/products/motion-tracking/9-axis/icm-20948/)
- AM2857: Dual H-Bridge Motor Driver
- SN65HVD230: CAN Transceiver

### Related Documentation
- [FIRMWARE_ARCHITECTURE.md](FIRMWARE_ARCHITECTURE.md) - Firmware design and structure
- [README.md](README.md) - Build instructions and overview
- [orbibot_config.h](include/orbibot_config.h) - Robot-specific configuration values

---

**Document Version**: 1.0
**Last Updated**: 2026-01-27
**Author**: Jewel Nath
**Status**: Complete hardware specification for OrbiBot firmware development
