# OrbiBot ROSMaster Firmware - Architecture Design

## Overview

Clean, professional STM32 firmware for OrbiBot mecanum-wheeled robot.
- **Target**: Yahboom ROSMaster V3.0 expansion board (STM32F103RCT6)
- **Robot**: OrbiBot with 100mm mecanum wheels
- **Purpose**: Motor control, encoder feedback, IMU data for ROS 2 integration

---

## Design Principles

1. **Simplicity**: Only features OrbiBot needs (no RGB, servos, SBUS, Ackermann)
2. **Readability**: Clear English comments, descriptive names
3. **Modularity**: Clean separation of concerns (HAL → Drivers → Application)
4. **Performance**: Real-time control with FreeRTOS
5. **Maintainability**: Well-documented, easy to modify

---

## Directory Structure

```
src/orbibot_rosmaster_firmware/
├── platformio.ini              # PlatformIO configuration
├── git_version.py              # Pre-build script (git hash injection)
├── README.md                   # Firmware documentation
├── firmware-architecture.md    # This file
├── hardware-doc.md             # Hardware specifications
├── firmware-issue.md           # Issue tracker
├── firmware-changelog.md       # Change history
│
├── include/                    # Public headers
│   ├── orbibot_config.h        # Robot-specific parameters
│   ├── firmware_version.h      # Version info (auto-generated string)
│   ├── robot_error.h           # Firmware-wide error codes
│   ├── FreeRTOSConfig.h        # FreeRTOS kernel config
│   ├── hal_*.h                 # HAL interfaces
│   ├── *_driver.h              # Driver interfaces
│   ├── protocol.h              # Protocol constants and API
│   ├── flash_storage.h         # Flash persistence API
│   └── task_*.h                # Task interfaces
│
├── src/
│   ├── main.c                  # Entry point, clock config, init, task creation
│   │
│   ├── hal/                    # Hardware Abstraction Layer
│   │   ├── hal_gpio.c          # GPIO control (motors, LEDs)
│   │   ├── hal_usart.c         # USART1 with DMA TX
│   │   ├── hal_timer.c         # PWM (TIM1/8) & encoder (TIM2-5)
│   │   ├── hal_i2c.c           # Software I2C for OLED
│   │   ├── hal_spi.c           # SPI2 for IMU
│   │   ├── hal_adc.c           # ADC for battery monitoring
│   │   └── hal_watchdog.c      # IWDG watchdog
│   │
│   ├── drivers/                # Device drivers
│   │   ├── motor_driver.c      # 4-channel H-bridge control
│   │   ├── encoder_driver.c    # Quadrature encoder reading
│   │   ├── imu_driver.c        # ICM-20948 IMU (SPI2)
│   │   ├── oled_driver.c       # SSD1306 OLED (optional)
│   │   ├── battery_monitor.c   # Battery voltage + EMA filter
│   │   └── flash_storage.c     # Flash persistence (PID, mag cal)
│   │
│   ├── control/                # Motion control
│   │   ├── mecanum_kinematics.c # Forward/inverse kinematics
│   │   ├── pid_controller.c     # Incremental PID with anti-windup
│   │   └── odometry.c           # Midpoint (RK2) odometry
│   │
│   ├── communication/          # Serial protocol
│   │   └── protocol.c          # RX state machine + TX reporting
│   │
│   └── tasks/                  # FreeRTOS tasks
│       ├── task_control.c      # Motion control (100Hz, prio 10)
│       ├── task_communication.c # Serial RX/TX (prio 7)
│       ├── task_imu.c          # IMU acquisition (50Hz, prio 8)
│       └── task_monitoring.c   # Battery, watchdog, LED (1Hz, prio 5)
│
├── tests/                      # Python test suite
│   ├── run_all_tests.py
│   ├── test_encoder.py
│   ├── test_imu.py
│   ├── test_motor_speed.py
│   └── test_beep.py
│
└── lib/                        # Third-party libraries
    ├── FreeRTOS/               # FreeRTOS v10.x kernel (src/ + inc/)
    └── STM32F10x_StdPeriph_Driver/  # STM32 Standard Peripheral Library
    # Note: lib/src/ was removed (was duplicate of lib/FreeRTOS/src/)
```

---

## Firmware Features

### ✅ Included (OrbiBot Essentials)

| Feature | Purpose | Update Rate |
|---------|---------|-------------|
| **Motor Control** | 4× PWM H-bridge for mecanum wheels | 100Hz PID loop |
| **Encoder Reading** | 4× quadrature encoders (1320 PPR) | Hardware capture |
| **Mecanum Kinematics** | Vx, Vy, ω → wheel speeds | Real-time |
| **Odometry** | Wheel encoders → position estimate | 100Hz (control loop rate) |
| **IMU Data** | ICM20948 9-axis (optional) | 50Hz |
| **Serial Protocol** | USART1 @ 115200 for ROS commands | Async |
| **Battery Monitor** | ADC voltage check, low battery warning | 1Hz |
| **OLED Status** | Optional status display | 10Hz |
| **Diagnostics** | System health, error reporting | 10Hz |

### ❌ Removed (Not Needed for OrbiBot)

- RGB LED strips (WS2812B)
- PWM servos (4 channels)
- Serial bus servos
- SBUS RC receiver
- Ackermann steering
- CAN bus
- Differential drive (use mecanum only)

---

## OrbiBot Robot Configuration

### Physical Parameters
```c
// Wheel configuration
#define WHEEL_RADIUS_M          0.050f   // 50mm radius
#define WHEEL_BASE_M            0.260f   // 260mm front-to-rear
#define TRACK_WIDTH_M           0.360f   // 360mm left-to-right

// Motor configuration
#define MOTOR_TYPE              MOTOR_JGB37_520
#define MOTOR_GEAR_RATIO        30.0f    // 1:30 gearbox
#define MOTOR_RPM_MAX           333      // No-load speed
#define ENCODER_PPR             1320     // Pulses per revolution (after gear)

// Mecanum wheel layout (ABBA pattern)
#define WHEEL_FL_TYPE           MECANUM_A  // Front-left: A-type
#define WHEEL_FR_TYPE           MECANUM_B  // Front-right: B-type
#define WHEEL_BL_TYPE           MECANUM_B  // Back-left: B-type
#define WHEEL_BR_TYPE           MECANUM_A  // Back-right: A-type
```

### Safety Limits
```c
#define MAX_LINEAR_VELOCITY     1.0f     // m/s
#define MAX_ANGULAR_VELOCITY    2.0f     // rad/s
#define BATTERY_VOLTAGE_MIN     10.5f    // Volts (4S LiFePO4 cutoff)
#define BATTERY_VOLTAGE_LOW     11.0f    // Volts (warning threshold)
#define COMMAND_TIMEOUT_MS      2000     // Stop if no command for 2s
```

---

## Control Architecture

### Task Hierarchy (FreeRTOS)

| Priority | Task | Rate | Responsibility |
|----------|------|------|----------------|
| 10 | `task_control` | 100Hz | Encoder read, PID, mecanum kinematics, odometry accumulation |
| 8 | `task_imu` | 50Hz | ICM-20948 read; accel→roll/pitch; gyro+mag→yaw (complementary filter) |
| 7 | `task_communication` | 1ms tick | USART RX command parse; 5-type auto-report at 20Hz each |
| 5 | `task_monitoring` | 1Hz | Watchdog feed, battery voltage, buzzer, LED heartbeat |

### Control Flow

```
ROS 2 → /cmd_vel
          ↓  [serial packet 0x12]
        USART ISR → protocol_receive_byte()
          ↓
        task_communication → protocol_parse_command()
          ↓
        mecanum_inverse_kinematics(Vx, Vy, ω)
          ↓
        task_control @ 100Hz
          ├── encoder_read_delta() × 4
          ├── pid_calculate_incremental() × 4
          ├── motor_set_pwm() × 4
          └── odometry_update()
                ↓  [serial packet 0x0A/0x0B/0x0C/0x0D/0x15]
              USART DMA TX → ROS 2 hardware_node
```

### Auto-Report Schedule (task_communication, 50ms cycle)

```
 0ms  ─ report_count=1  → REPORT_SPEED   (0x0A) — Vx/Vy/Vz + battery
10ms  ─ report_count=5  → REPORT_ICM_RAW (0x0E) — calibrated gyro/accel + raw mag
20ms  ─ report_count=9  → REPORT_IMU_ATT (0x0C) — roll/pitch/yaw
30ms  ─ report_count=13 → REPORT_ENCODER (0x0D) — 4 encoder counts
40ms  ─ report_count=17 → REPORT_ODOM    (0x15) — x/y/theta/vx/vy/omega
20ms  ─ cycle repeats   (all types at 50Hz = 250 packets/sec)
```

---

## Communication Protocol

### Serial Interface
- **Port**: USART1 (115200 baud, 8N1)
- **Connection**: USB-C (CH340N) to Raspberry Pi 5
- **Format**: Yahboom-compatible binary protocol

### Packet Structure
```
[0xFF] [Device_ID] [Length] [Function] [Data...] [Checksum]
```
- **Device ID receive** (host → firmware): `0xFC`
- **Device ID send** (firmware → host): `0xFB`
- **Checksum**: additive sum of Length + Function + Data bytes (NOT Device_ID), truncated to `uint8_t`

### Function Codes

**Incoming (host → firmware):**
| Code | Name | Description |
|------|------|-------------|
| `0x01` | AUTO_REPORT | Enable/disable 20Hz data streaming |
| `0x02` | BEEP | Buzzer: 0=off, 1=continuous, ≥10=duration ms |
| `0x09` | RESET_ODOM | Reset firmware x/y/theta position to zero |
| `0x0F` | RESET_STATE | Reset protocol state machine |
| `0x12` | MOTION | 3D velocity: Vx, Vy, Vz as int16 (mm/s × 1000) |
| `0x13` | SET_MOTOR_PID | Single-level gains (Kp/Ki/Kd int16 × 1000) + save byte |
| `0x14` | SET_YAW_PID | Yaw gains (Kp/Ki/Kd int16 × 1000) + save byte |
| `0x16` | SET_MAG_CAL | Hard-iron offsets (int16 × 100 µT per axis) |
| `0x08` | RESET_ENCODERS | Reset encoder counts to zero (odometry unchanged) |
| `0x50`+`0x51` | VERSION | Send REQUEST_DATA (0x50) with sub-byte 0x51 |

**Outgoing (firmware → host), auto-reported at 20Hz each (50ms cycle, interleaved 10ms):**
| Code | Name | Description |
|------|------|-------------|
| `0x0A` | REPORT_SPEED | Vx, Vy, Vz (int16 mm/s) + battery (uint8 × 0.1V) |
| `0x0E` | REPORT_ICM_RAW | Gyro milli-rad/s + accel milli-m/s² + mag raw counts (int16) |
| `0x0C` | REPORT_IMU_ATT | Roll, pitch, yaw (int16 × 10000 rad) |
| `0x0D` | REPORT_ENCODER | FL, BL, FR, BR encoder counts (int32 LE ticks) |
| `0x15` | REPORT_ODOM | x, y, theta (int32) + vx, vy, omega (int32) — mm/mrad units |

> Full field layouts: see `include/protocol.h` and `src/communication/protocol.c`

---

## Mecanum Kinematics

### Forward Kinematics (Wheel speeds → Robot velocity)
```
Vx = (ωFL + ωFR + ωBL + ωBR) × r / 4
Vy = (-ωFL + ωFR + ωBL - ωBR) × r / 4
ω  = (-ωFL + ωFR - ωBL + ωBR) × r / (4 × (lx + ly))

Where:
- ω = wheel angular velocity (rad/s)
- r = wheel radius (m)
- lx = wheelbase / 2 (m)
- ly = track width / 2 (m)
```

### Inverse Kinematics (Robot velocity → Wheel speeds)
```
ωFL = (Vx - Vy - (lx + ly) × ω) / r
ωFR = (Vx + Vy + (lx + ly) × ω) / r
ωBL = (Vx + Vy - (lx + ly) × ω) / r
ωBR = (Vx - Vy + (lx + ly) × ω) / r
```

---

## PID Control

### Motor Speed Control (Incremental PID)

Single PID gains — sufficient for OrbiBot's indoor speed range (100-500 mm/s).

```c
// Default gains (runtime-tunable via serial, persisted to flash)
Kp = 0.8    // Proportional
Ki = 0.06   // Integral (trapezoidal integration)
Kd = 0.5    // Derivative
```

**Formula (incremental):**
```
deltaOut = Kp*(e[k] - e[k-1]) + Ki*0.5*(e[k] + e[k-1]) + Kd*(e[k] - 2*e[k-1] + e[k-2])
Out[k] = Out[k-1] + deltaOut
```

**Anti-windup:** Conditional integral clamp at +/-4000. Stops I accumulation when
output is saturated in the same direction as the error.

### Control Loop (100Hz)
```
1. Read encoder positions → Calculate wheel velocities
2. Compare target vs actual velocity → Compute error
3. PID calculation → PWM duty cycle
4. Apply PWM to motor H-bridge
5. Repeat every 10ms
```

---

## Memory Budget

### Flash (256KB total)
- Firmware code + FreeRTOS: ~38KB (~15%)
- Unused: ~224KB (>85% free for future features)

### RAM (48KB total)
- FreeRTOS heap: 20KB
- Task stacks: ~5KB (4 tasks; CommTask uses 2KB)
- Global variables: ~2KB
- In use: ~19.5KB (~40%)
- Free: ~29KB (~60%)

---

## Build Configuration (platformio.ini)

```ini
[platformio]
src_dir = src
include_dir = include

[env:orbibot]
platform = ststm32
board = genericSTM32F103RC
framework = cmsis
extra_scripts = pre:git_version.py   # Injects GIT_COMMIT_HASH + GIT_BRANCH

upload_protocol = serial
upload_port = /dev/motordriver
monitor_speed = 115200

build_flags =
    -D STM32F10X_HD
    -D USE_STDPERIPH_DRIVER
    -D ORBIBOT_FIRMWARE
    -I include
    -I lib/FreeRTOS/inc
    -I lib/STM32F10x_StdPeriph_Driver/inc
    -Os
    -Wall -Wextra -Werror             # All warnings are errors
    -Wno-unused-parameter             # Allowed (common in HAL callbacks)
    -ffunction-sections -fdata-sections  # Dead code elimination

build_src_filter =
    +<**/*.c>
    +<../lib/FreeRTOS/src/*.c>
    +<../lib/STM32F10x_StdPeriph_Driver/src/*.c>
```

**Debug vs Production:** Set `ENABLE_DEBUG_OUTPUT=1` and `ENABLE_BOOT_MESSAGES=1`
in `orbibot_config.h` for bench debugging with serial monitor. Keep both at 0 for
production — debug printf shares USART1 with the binary protocol and will corrupt data.

---

## Testing Plan

### Phase 1: Hardware Verification
- [ ] USART communication (115200 baud)
- [ ] GPIO outputs (motor direction pins)
- [ ] PWM generation (4 channels, 20kHz)
- [ ] Encoder capture (4 channels, quadrature)
- [ ] IMU SPI communication
- [ ] Battery ADC reading

### Phase 2: Driver Testing
- [ ] Motor forward/reverse/stop
- [ ] Encoder counting accuracy
- [ ] IMU data acquisition
- [ ] OLED display (if enabled)

### Phase 3: Control Testing
- [ ] PID loop stability
- [ ] Velocity command response
- [ ] Odometry accuracy (measure vs actual)
- [ ] Safety features (timeout, battery)

### Phase 4: Integration Testing
- [ ] ROS 2 command → motor response
- [ ] Odometry publishing
- [ ] IMU data publishing
- [ ] Full system stress test

---

## Development Workflow

### 1. Initial Setup
```bash
cd ~/OrbiBot/src/orbibot_rosmaster_firmware
platformio init
```

### 2. Build
```bash
platformio run
```

### 3. Upload
```bash
# Put board in bootloader mode (BOOT0 + RESET)
platformio run --target upload
```

### 4. Monitor
```bash
platformio device monitor --baud 115200
```

### 5. Debug
```bash
# With ST-Link connected to SWD pins
platformio run --target debug
```

---

## Code Style Guidelines

### Naming Conventions
```c
// Constants: UPPER_SNAKE_CASE
#define MAX_VELOCITY 1.0f

// Types: snake_case_t
typedef struct { ... } motor_state_t;

// Functions: snake_case with module prefix
void motor_driver_set_pwm(uint8_t channel, float duty);

// Variables: snake_case
float current_velocity;
```

### Comments
```c
/**
 * @brief Brief description
 * @param param1 Description of param1
 * @return Description of return value
 */
```

### File Headers
```c
/**
 * @file motor_driver.c
 * @brief 4-channel H-bridge motor driver for OrbiBot
 * @author Jewel Nath
 * @date 2025-11-27
 */
```

---

## Version Control

### Branching Strategy
- `main` - Stable releases only
- `develop` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes

### Commit Messages
```
feat: Add mecanum kinematics module
fix: Correct encoder overflow handling
refactor: Simplify PID controller code
docs: Update architecture diagram
test: Add motor driver unit tests
```

---

## Future Enhancements (Post-MVP)

### Optional Features
- [ ] Visual odometry fusion (RealSense D435)
- [ ] EKF sensor fusion (IMU + wheel + visual)
- [ ] Autonomous navigation waypoints
- [ ] Web dashboard for monitoring
- [ ] OTA firmware updates via ROS
- [ ] Motor current sensing
- [ ] Wheel slip detection

---

## References

### OrbiBot Documentation
- [HARDWARE_DOC.md](HARDWARE_DOC.md) - Complete hardware specifications
- [README.md](README.md) - Build instructions and firmware overview
- [OrbiBot ROS 2 Packages](../../src/)

### External Resources
- [STM32F103 Reference Manual](https://www.st.com/resource/en/reference_manual/cd00171190.pdf)
- [STM32F103 Datasheet](https://www.st.com/resource/en/datasheet/stm32f103rc.pdf)
- [FreeRTOS Documentation](https://www.freertos.org/Documentation/RTOS_book.html)
- [Yahboom ROSMaster GitHub](https://github.com/YahboomTechnology/ROS-robot-expansion-board)

---

**Architecture Version**: 2.3
**Last Updated**: 2026-03-25
**Status**: Implemented and Active
