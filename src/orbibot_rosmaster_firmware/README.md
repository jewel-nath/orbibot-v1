# OrbiBot ROSMaster Firmware

**Clean, OrbiBot-specific firmware for the Yahboom ROSMaster V3.0 Expansion Board**

## Overview

This firmware is specifically designed for the OrbiBot mecanum-wheeled robot, replacing the original Yahboom firmware with a clean, well-documented implementation focused on OrbiBot's needs.

### Key Features

- **OrbiBot-Specific Configuration** — 50mm wheel radius, 360mm track width, 260mm wheelbase, ABBA mecanum layout
- **ICM-20948 9-Axis IMU** — SPI2 @ 4.5MHz, 50Hz update, gyro calibration, magnetometer with DRDY cache
- **Clean Architecture** — Modular HAL / Driver / Control / Task layers with FreeRTOS
- **Safety Hardened** — Battery lockout, per-task watchdog, HSE fallback, fault-safe handlers
- **Production Build** — `-Werror`, zero debug output, git version injection

### Firmware Statistics

- **Flash Usage**: ~38 KB / 256 KB (~15%)
- **RAM Usage**: ~19.5 KB / 48 KB (~40%)
- **Source Files**: 24 C files + 19 headers
- **Build System**: PlatformIO + GCC ARM Embedded
- **RTOS**: FreeRTOS v10.x with 4 tasks

---

## Quick Start

### Build & Upload

```bash
cd src/orbibot_rosmaster_firmware

# Build firmware
~/.platformio/penv/bin/pio run

# Upload (set BOOT0=HIGH, press RESET, then run)
~/.platformio/penv/bin/pio run --target upload

# After upload: set BOOT0=LOW, press RESET

# Monitor serial output (115200 baud)
~/.platformio/penv/bin/pio device monitor
```

### Verify on Robot

```bash
# From the RPi 5 — start the ROS 2 hardware node
ros2 launch orbibot_hardware hardware.launch.py

# Check topics
ros2 topic hz /odom              # Should be ~20Hz
ros2 topic hz /imu/data_raw      # Should be ~20Hz (interleaved)
ros2 topic echo /orbibot/system_status  # Battery voltage

# Test motors
ros2 launch orbibot_teleop controller.launch.py  # Gamepad control
```

---

## Architecture

### Directory Structure

```
orbibot_rosmaster_firmware/
├── src/
│   ├── main.c                         # Entry point, clock config, task creation
│   ├── hal/                           # Hardware Abstraction Layer
│   │   ├── hal_gpio.c                 #   GPIO initialization
│   │   ├── hal_usart.c                #   USART1 + DMA TX + printf _write()
│   │   ├── hal_timer.c                #   PWM (TIM1/8) + encoder capture (TIM2-5)
│   │   ├── hal_spi.c                  #   SPI2 for ICM-20948 (with timeout)
│   │   ├── hal_adc.c                  #   ADC for battery monitoring
│   │   ├── hal_watchdog.c             #   IWDG independent watchdog
│   │   ├── hal_i2c.c                  #   Software I2C on PA2/PA3 (OLED)
│   │   └── hal_ssd1306.c             #   SSD1306 OLED low-level (stub)
│   ├── drivers/                       # Device Drivers
│   │   ├── motor_driver.c             #   4-channel H-bridge control
│   │   ├── encoder_driver.c           #   Quadrature encoder reading
│   │   ├── imu_driver.c              #   ICM-20948 9-axis IMU (SPI2)
│   │   ├── battery_monitor.c          #   Battery ADC + EMA filter
│   │   ├── flash_storage.c            #   Flash persistence (PID + mag cal)
│   │   ├── oled_driver.c             #   SSD1306 OLED display (stub)
│   │   └── oled_fonts.c              #   Font data for OLED
│   ├── control/                       # Control Algorithms
│   │   ├── pid_controller.c           #   Multi-level incremental PID
│   │   ├── mecanum_kinematics.c       #   Inverse + forward kinematics
│   │   └── odometry.c                #   Midpoint (RK2) integration
│   ├── communication/                 # Serial Protocol
│   │   └── protocol.c                #   RX state machine, command dispatch, auto-report
│   └── tasks/                         # FreeRTOS Tasks
│       ├── task_control.c             #   Motion control (100Hz, priority 10)
│       ├── task_imu.c                 #   IMU acquisition (50Hz, priority 8)
│       ├── task_communication.c       #   Serial RX/TX (async, priority 7)
│       └── task_monitoring.c          #   Battery + watchdog (1Hz, priority 5)
├── include/                           # Headers
│   ├── orbibot_config.h               #   All robot parameters (geometry, PID, thresholds)
│   ├── firmware_version.h             #   Version macros + git hash
│   ├── robot_error.h                 #   Unified error enum (robot_err_t)
│   ├── FreeRTOSConfig.h              #   FreeRTOS settings
│   ├── protocol.h                    #   Protocol function codes + API
│   ├── hal_*.h, *_driver.h, task_*.h  #   Module interfaces
│   └── stm32f10x.h, core_cm3.h       #   CMSIS + device headers
├── lib/                               # Libraries
│   ├── src/                           #   FreeRTOS kernel sources
│   └── STM32F10x_StdPeriph_Driver/    #   STM32 Standard Peripheral Library
├── tests/                             # Python test suite (serial)
│   ├── run_all_tests.py               #   Run full test suite
│   ├── rosmaster_protocol.py          #   Protocol helper library
│   ├── test_encoder.py               #   Encoder direction verification
│   ├── test_imu.py                   #   IMU raw + attitude data
│   ├── test_motor_speed.py           #   PWM sweep all 4 motors
│   ├── test_motor_direction.py       #   Motor direction verification
│   ├── test_beep.py                  #   Buzzer pattern test
│   ├── test_battery.py               #   Battery voltage readout
│   ├── test_odometry.py              #   Firmware odometry report
│   ├── test_pid.py                   #   PID gain read/write
│   ├── test_safety.py               #   Safety feature tests
│   ├── test_data_rate.py            #   Auto-report rate measurement
│   ├── test_version.py              #   Firmware version query
│   └── test_oled.py                 #   OLED display test
├── platformio.ini                     # Build configuration
├── git_version.py                     # Pre-build: injects git hash + branch
├── README.md                          # This file
├── firmware-architecture.md           # Detailed architecture document
├── hardware-doc.md                    # Complete hardware specifications
├── firmware-changelog.md              # Full change history
└── firmware-issue.md                  # Open issues & future work
```

### Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  FreeRTOS Tasks                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ control  │ │   imu    │ │communication │ │  monitoring  │      │
│  │  100Hz   │ │  50Hz    │ │   async      │ │    1Hz       │      │
│  │  pri 10  │ │  pri 8   │ │   pri 7      │ │   pri 5      │      │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ └──────┬───────┘      │
├───────┼────────────┼───────────────┼────────────────┼───────────────┤
│  Control Algorithms                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                           │
│  │   PID    │ │ Mecanum  │ │ Odometry │                            │
│  │ 4-motor  │ │ ABBA kin │ │ RK2 integ│                            │
│  └──────────┘ └──────────┘ └──────────┘                            │
├────────────────────────────────────────────────────────────────────┤
│  Drivers                                                            │
│  ┌───────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌───────┐           │
│  │ Motor │ │Encoder │ │  IMU   │ │ Battery │ │ Flash │            │
│  │4× PWM │ │4× Quad │ │ICM2094│ │ADC+EMA  │ │ PID+  │            │
│  │       │ │        │ │8 9-axis│ │         │ │ MagCal│            │
│  └───┬───┘ └───┬────┘ └───┬────┘ └────┬────┘ └───┬───┘            │
├──────┼─────────┼──────────┼───────────┼──────────┼─────────────────┤
│  HAL (Hardware Abstraction Layer)                                   │
│  ┌──────┐ ┌───────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌────────┐         │
│  │ GPIO │ │ Timer │ │ SPI2 │ │ ADC │ │USART│ │Watchdog│          │
│  │      │ │PWM+Enc│ │      │ │     │ │+DMA │ │  IWDG  │          │
│  └──────┘ └───────┘ └──────┘ └─────┘ └─────┘ └────────┘          │
├────────────────────────────────────────────────────────────────────┤
│  STM32F103RCT6 Hardware (72MHz Cortex-M3, 256KB Flash, 48KB RAM)   │
└────────────────────────────────────────────────────────────────────┘
```

### FreeRTOS Tasks

| Task | Rate | Priority | Stack | Responsibility |
|------|------|----------|-------|----------------|
| `task_control` | 100Hz | 10 | 512 words | PID control, encoder read, kinematics, odometry |
| `task_imu` | 50Hz | 8 | 1024 words | IMU SPI read (sole reader), attitude computation |
| `task_communication` | async | 7 | 512 words | Protocol RX dispatch, auto-report TX (5 types @ 20Hz) |
| `task_monitoring` | 1Hz | 5 | 512 words | Battery check, per-task alive verification, watchdog feed |

---

## Safety Features (v2.0.0)

| Feature | Description |
|---------|-------------|
| **Battery lockout** | Motors refuse commands when voltage < 10.5V; auto-unlocks above 11.0V (hysteresis) |
| **Per-task watchdog** | Each task increments an alive counter; watchdog only fed if all tasks are alive |
| **HSE fallback** | If external crystal fails, MCU falls back to HSI @ 36MHz (degraded but operational) |
| **Fault-safe handlers** | HardFault/StackOverflow/MallocFailed use direct USART register writes (no heap/printf) |
| **Bounds checking** | All motor/encoder index parameters validated (>= 4 returns immediately) |
| **Thread safety** | Critical sections on all shared data (IMU attitude, measured velocity, odometry) |
| **DMA timeout** | USART DMA TX has ~2ms timeout; disables channel on stall |
| **SPI timeout** | All SPI2 transfers have timeout to prevent infinite loops |

---

## Hardware Configuration

### STM32F103RCT6 Pinout

> Pin configurations verified against actual Yahboom firmware source code

**Motor Driver (AM2857 x 4, 12V, 20kHz PWM, resolution 0-3600):**

| Motor | Position | Timer | PWM_A Pin | PWM_B Pin |
|-------|----------|-------|-----------|-----------|
| M1 | Front-Left | TIM8 CH1/CH2 | PA11 | PA8 |
| M2 | Back-Left | TIM8 CH3/CH4 | PB0 | PB1 |
| M3 | Front-Right | TIM1 CH4/CH1 | PC6 | PC7 |
| M4 | Back-Right | TIM1 CH2/CH3 | PC8 | PC9 |

> M2 uses PB0/PB1 (not PA9/PA10) to avoid USART1 conflict.

**Encoders (Quadrature Hall Effect, 1320 PPR, 3.3V):**

| Motor | Timer | Encoder A | Encoder B |
|-------|-------|-----------|-----------|
| M1 | TIM2 | PA15 | PB3 |
| M2 | TIM4 | PB6 | PB7 |
| M3 | TIM5 | PA0 | PA1 |
| M4 | TIM3 | PA6 | PA7 |

**IMU (ICM-20948 via SPI2 @ 4.5MHz, Mode 0):**

| Pin | Function |
|-----|----------|
| PB12 | CS (NSS) |
| PB13 | SCK |
| PB14 | MISO |
| PB15 | MOSI |

**Other Peripherals:**

| Peripheral | Pin(s) | Notes |
|------------|--------|-------|
| USART1 TX/RX | PA9/PA10 | 115200 8N1, DMA TX |
| Battery ADC | PC4 (CH14) | 4S LiFePO4 voltage divider |
| Buzzer | PC5 | Active, 5V via SS8050 |
| KEY1 | PD2 | User button, active-low |
| OLED (SSD1306) | PA2/PA3 | Software I2C (PB6/PB7 conflicts with TIM4 encoder) |
| USB (CH340N) | PA11/PA12 | Type-C connector |

**Power Rails:**

| Rail | Voltage | Usage |
|------|---------|-------|
| VM | 12V | Motors |
| VCC_5V | 5V | USB, buzzer, OLED |
| VCC_3V3 | 3.3V | MCU, IMU, encoders |

### Battery Thresholds (4S LiFePO4)

| State | Voltage | Action |
|-------|---------|--------|
| Full | 14.6V | Normal operation |
| Nominal | 12.8V | Normal operation |
| Low warning | 11.0V | Buzzer warning, lockout clears above this |
| Critical | 10.5V | Motors stopped, lockout set, continuous buzzer |

---

## PID Control

Multi-level incremental PID with gains interpolated by wheel speed (100Hz):

| Level | Speed Range | Kp | Ki | Kd |
|-------|-------------|-----|------|-----|
| 0 | Low speed | 0.8 | 0.06 | 0.5 |
| 1 | Medium speed | 0.8 | 0.06 | 0.5 |
| 2 | High speed | 0.8 | 0.06 | 0.5 |

> Gains and speed thresholds are runtime-tunable via serial protocol and persisted to flash.

**Incremental PID formula:**
```
deltaOut = Kp * (Ek - Ek_1) + Ki * Ek + Kd * (Ek - 2*Ek_1 + Ek_2)
Out_k = Out_k_1 + deltaOut
```

Anti-windup: output saturated at +/-3600 (max PWM).

---

## Mecanum Kinematics

**ABBA wheel layout:**
```
Front-Left (A)  \   /  Front-Right (B)
                 \ /
                 / \
Rear-Left  (B)  /   \  Rear-Right  (A)
```

**Robot geometry:**
- Track width (2a): 360mm
- Wheelbase (2b): 260mm
- Wheel radius: 50mm

**Inverse kinematics (chassis velocity -> wheel speeds):**
```
V_FL = Vx - Vy - (a + b) * omega
V_FR = Vx + Vy + (a + b) * omega
V_RL = Vx + Vy - (a + b) * omega
V_RR = Vx - Vy + (a + b) * omega
```

**Odometry:** Midpoint (RK2) integration at 100Hz — uses `mid_theta = theta + delta_theta/2` for reduced drift during combined rotation and translation.

---

## Serial Protocol

**Packet format:** `[0xFF] [Device_ID] [Length] [Function] [Data...] [Checksum]`
- Host -> Firmware: Device ID `0xFC`
- Firmware -> Host: Device ID `0xFB`
- Checksum: additive sum of all bytes from Device_ID through last data byte, truncated to `uint8_t`
- Double-buffered RX with drop counting (no packet loss under load)

### Function Codes

| Code | Dir | Name | Data |
|------|-----|------|------|
| `0x01` | H->F | `AUTO_REPORT` | `[enable]` — 1=stream, 0=stop |
| `0x02` | H->F | `BEEP` | `[dur_lo][dur_hi]` — 0=off, 1=continuous, >=10=ms |
| `0x09` | H->F | `RESET_ODOM` | _(no data)_ — reset position/heading to zero |
| `0x0F` | H->F | `RESET_STATE` | _(no data)_ — restart protocol state machine |
| `0x12` | H->F | `MOTION` | `[car_type][vx_lo][vx_hi][vy_lo][vy_hi][vz_lo][vz_hi]` |
| `0x13` | H->F | `SET_MOTOR_PID` | `[kp][ki][kd]` as int16 x 1000 + `[save]` flag |
| `0x14` | H->F | `SET_YAW_PID` | `[kp][ki][kd]` as int16 x 1000 + `[save]` flag |
| `0x16` | H->F | `SET_MAG_CAL` | `[ox][oy][oz]` as int16 offset x 100 |
| `0x18` | H->F | `SET_PID_MULTILEVEL` | 3 thresholds + 9 gains + save flag |
| `0x51` | H->F | `VERSION` | _(no data)_ — request firmware version |
| `0x0A` | F->H | `REPORT_SPEED` | `[vx][vy][vz]` int16 mm/s x1000 + `[bat]` uint8 x0.1V |
| `0x0B` | F->H | `REPORT_IMU_RAW` | `[gx][gy][gz][ax][ay][az][mx][my][mz]` raw int16 |
| `0x0C` | F->H | `REPORT_IMU_ATT` | `[roll][pitch][yaw]` int16 x 1000 rad |
| `0x0D` | F->H | `REPORT_ENCODER` | `[m1][m2][m3][m4]` as int32 LE ticks |
| `0x15` | F->H | `REPORT_ODOM` | `[x][y][theta]` int32 + `[vx][vy][omega]` int16 |

### Auto-Report Schedule (20Hz each, interleaved)

| Cycle | Report | Code |
|-------|--------|------|
| 1 | Speed + Battery | `0x0A` |
| 11 | IMU Raw | `0x0B` |
| 21 | IMU Attitude | `0x0C` |
| 31 | Encoder counts | `0x0D` |
| 41 | Firmware Odometry | `0x15` |

> Full packet format details: see [firmware-architecture.md](firmware-architecture.md)

---

## Configuration Reference

All configurable parameters are in `include/orbibot_config.h`:

| Section | Key Parameters |
|---------|---------------|
| **Robot Geometry** | `WHEEL_DIAMETER_M` (0.1), `TRACK_WIDTH_M` (0.36), `WHEELBASE_M` (0.26) |
| **Encoder** | `ENCODER_CPR` (1320), `GEAR_RATIO` (30) |
| **Motor** | `MAX_RPM` (333), `MAX_PWM` (3600), `PWM_FREQUENCY` (20000) |
| **Velocity Limits** | `MAX_LINEAR_VELOCITY_MPS` (1.0), `MAX_ANGULAR_VELOCITY_RPS` (2.0) |
| **PID** | `MOTOR_PID_KP/KI/KD`, `YAW_PID_*`, speed thresholds |
| **Battery** | `BATTERY_VOLTAGE_LOW` (11.0), `BATTERY_VOLTAGE_CRITICAL` (10.5) |
| **IMU** | `IMU_UPDATE_RATE_HZ` (50), `IMU_GYRO_SCALE`, `IMU_ACCEL_SCALE` |
| **Tasks** | Stack sizes, update rates for each FreeRTOS task |
| **Debug** | `ENABLE_DEBUG_OUTPUT` (0), `DEBUG_LEVEL` (0), `ENABLE_BOOT_MESSAGES` (0) |

> Set `ENABLE_DEBUG_OUTPUT=1` and `ENABLE_BOOT_MESSAGES=1` for bench debugging with serial monitor. Keep both at 0 for production (debug printf corrupts the binary protocol on shared USART1).

---

## Debugging

### Firmware Test Suite

```bash
cd src/orbibot_rosmaster_firmware/tests

# Full test run (requires robot connected via /dev/motordriver)
python3 run_all_tests.py --port /dev/motordriver

# Individual tests
python3 test_encoder.py          # Spin wheels by hand, verify direction
python3 test_imu.py              # IMU raw + attitude at 50Hz
python3 test_motor_speed.py      # PWM sweep all 4 motors
python3 test_motor_direction.py  # Motor direction verification
python3 test_beep.py             # Buzzer pattern test
python3 test_battery.py          # Battery voltage readout
python3 test_odometry.py         # Firmware odometry report
python3 test_pid.py              # PID gain read/write
python3 test_safety.py           # Safety feature tests
python3 test_data_rate.py        # Auto-report rate measurement
python3 test_version.py          # Firmware version query
```

### ROS 2 Debug Commands

```bash
# Start hardware node
ros2 launch orbibot_hardware hardware.launch.py

# Check topic rates
ros2 topic hz /odom                          # ~20Hz
ros2 topic hz /imu/data_raw                  # ~20Hz
ros2 topic hz /imu/data                      # ~20Hz

# Inspect data
ros2 topic echo /odom --once
ros2 topic echo /orbibot/system_status       # Battery, motor state

# Trigger beep
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 200"

# Reset odometry
ros2 service call /orbibot/reset_odometry std_srvs/srv/Empty

# Check serial port
ls -la /dev/motordriver   # symlink to /dev/ttyUSB0 or ttyACM0
```

### Common Hardware Issues

| Symptom | Check |
|---------|-------|
| No serial data | BOOT0 must be LOW after upload; press RESET |
| Wrong encoder direction | `test_encoder.py` — rotate wheel by hand |
| IMU returns 0 | WHO_AM_I must return `0xEA`; check SPI2 wiring (PB12-PB15) |
| Battery reads 0V | ADC on PC4 (ADC_Channel_14); check 4S divider resistors |
| Motors don't respond | Verify `AUTO_REPORT` enabled; check 12V supply |
| Odometry drift | Verify wheel radius (50mm) and encoder CPR (1320) in config |
| Motors stop unexpectedly | Battery lockout — check voltage > 10.5V |

### Serial Monitor

```bash
# Direct serial access (Ctrl+A K to quit)
screen /dev/motordriver 115200

# Or use PlatformIO
~/.platformio/penv/bin/pio device monitor
```

---

## Why Custom Firmware?

### The Problem with Yahboom's Original Firmware

The Yahboom ROSMaster V3.0 board ships with proprietary firmware that has several limitations:
- **Closed Source**: Binary blob with no source code access
- **Fixed Configuration**: Hardcoded for Yahboom X3 robot (60mm wheels, 300mm track width)
- **Bloated**: ~150KB Flash (60%) with many unused features
- **Limited Documentation**: Minimal English documentation
- **Hard to Customize**: Cannot modify kinematics, PID tuning, or control algorithms

### Comparison

| Feature | Yahboom Original | OrbiBot Custom |
|---------|-----------------|----------------|
| Source Code | Closed binary | Open source |
| Flash Usage | ~150 KB (60%) | ~38 KB (15%) |
| Configuration | Hardcoded | `orbibot_config.h` |
| Kinematics | Fixed differential | Mecanum-specific |
| Documentation | Chinese/minimal | English/comprehensive |
| Build System | Keil MDK (proprietary) | PlatformIO (free) |
| Safety | Basic | Battery lockout, per-task watchdog, HSE fallback |
| Build Quality | Unknown | `-Werror`, no implicit declarations |

### Hardware on ROSMaster V3.0 Not Used by OrbiBot

| Hardware | Board Support | Firmware |
|----------|--------------|---------|
| RGB LED (WS2812B) | on board | excluded |
| PWM Servos (4ch) | on board | excluded |
| SBUS RC receiver | on board | excluded |
| Ackermann steering | on board | excluded |
| CAN bus (SN65HVD230) | on board | excluded |
| OLED display (SSD1306) | on board | stub present |

---

## Build System Notes

### Build Flags

The firmware builds with strict warnings enabled:
- `-Wall -Wextra -Werror` — all warnings are build errors
- `-Wno-unused-parameter` — allowed (common in HAL callbacks)
- `-ffunction-sections -fdata-sections` — dead code elimination

### Git Version Injection

`git_version.py` runs as a PlatformIO pre-build script, injecting:
- `GIT_COMMIT_HASH` — short git hash (e.g., `"a1b2c3d"`)
- `GIT_BRANCH` — current branch (e.g., `"main"`)

These appear in the firmware version response (function code `0x51`).

### Debug vs Production

| Setting | Production | Debug |
|---------|-----------|-------|
| `ENABLE_DEBUG_OUTPUT` | 0 | 1 |
| `DEBUG_LEVEL` | 0 | 1+ (1=Error, 2=Info, 3=Verbose) |
| `ENABLE_BOOT_MESSAGES` | 0 | 1 |

> In debug mode, `printf` output shares USART1 with the binary protocol. Use debug mode only with a serial monitor, not with the ROS 2 driver.

---

## Lessons from PlatformIO Migration

Key issues encountered migrating from Keil MDK to PlatformIO GCC:

1. **Printf support**: Keil uses `fputc()`, GCC newlib requires `_write()` syscall — implemented in `hal_usart.c`
2. **SPI timeout protection**: Added timeout to all SPI transfers to prevent firmware hang
3. **FreeRTOS-safe delays**: `imu_delay_ms()` uses DWT cycle counter for accurate pre-scheduler delays (SysTick not available)

---

## Documentation

| Document | Contents |
|----------|----------|
| [firmware-architecture.md](firmware-architecture.md) | Detailed architecture, data flow, protocol packet formats |
| [hardware-doc.md](hardware-doc.md) | Complete hardware specs, pin mappings, electrical details |
| [firmware-changelog.md](firmware-changelog.md) | Full change history (v1.x and v2.0.0) |
| [firmware-issue.md](firmware-issue.md) | Open issues and future work |
| [orbibot_config.h](include/orbibot_config.h) | All configurable parameters |
| [tests/README.md](tests/README.md) | Test suite documentation |

---

## Version

- **Version**: v2.0.0
- **Target**: STM32F103RCT6 (72MHz Cortex-M3, 48KB RAM, 256KB Flash)
- **Board**: Yahboom ROSMaster V3.0
- **Robot**: OrbiBot (mecanum-wheeled mobile robot)
- **Author**: Jewel Nath
- **Date**: March 2026

## References

- **Yahboom ROSMaster V3.0**: https://github.com/YahboomTechnology/ROS-robot-expansion-board
- **ICM-20948 Datasheet**: InvenSense DS-000189
- **STM32F103RCT6 Reference Manual**: RM0008
- **PlatformIO**: https://platformio.org/
