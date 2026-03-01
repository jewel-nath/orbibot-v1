# Part 9: Project Structure

**Duration**: 15 minutes  
**Prerequisites**: [60-pid-controllers.md](60-pid-controllers.md)

---

## Learning Objectives

After this lesson, you will understand:
- How the firmware codebase is organized
- What each directory contains
- Key files and their purposes
- The build system (PlatformIO)

---

## Directory Structure

```
orbibot_rosmaster_firmware/
├── src/                          # Source code
│   ├── main.c                   # Application entry point
│   ├── hal/                     # Hardware Abstraction Layer
│   │   ├── hal_gpio.c          # GPIO control
│   │   ├── hal_timer.c         # Timers and PWM
│   │   ├── hal_usart.c         # Serial communication
│   │   ├── hal_spi.c           # SPI bus (IMU)
│   │   ├── hal_adc.c           # ADC (battery)
│   │   └── ...
│   ├── drivers/                 # Device drivers
│   │   ├── motor_driver.c      # Motor control
│   │   ├── encoder_driver.c    # Encoder reading
│   │   ├── imu_driver.c        # IMU sensor
│   │   ├── battery_monitor.c   # Battery voltage
│   │   └── ...
│   ├── tasks/                   # FreeRTOS tasks
│   │   ├── task_control.c      # Motor PID (100Hz)
│   │   ├── task_communication.c # Serial handling
│   │   ├── task_imu.c          # IMU reading (50Hz)
│   │   └── task_monitoring.c   # Health check (1Hz)
│   ├── control/                 # Control algorithms
│   │   ├── pid_controller.c    # PID implementation
│   │   ├── mecanum_kinematics.c # Wheel math
│   │   └── odometry.c          # Position tracking
│   └── communication/           # Protocol
│       └── protocol.c          # Packet parsing
│
├── include/                     # Header files
│   ├── orbibot_config.h        # Robot configuration
│   ├── firmware_version.h      # Version info
│   ├── hal_*.h                 # HAL interfaces
│   ├── *_driver.h              # Driver interfaces
│   ├── task_*.h                # Task interfaces
│   └── ...
│
├── lib/                         # Libraries
│   ├── FreeRTOS/               # FreeRTOS kernel
│   └── STM32F10x_StdPeriph_Driver/ # STM32 library
│
├── tests/                       # Test scripts
│   ├── test_encoder.py
│   ├── test_motor.py
│   └── ...
│
├── platformio.ini              # Build configuration
├── README.md                   # Documentation
├── firmware-architecture.md    # Architecture details
└── firmware-issue.md           # Known issues
```

---

## Key Files Explained

### main.c - Entry Point

```c
// src/main.c - Application entry point

int main(void)
{
    // 1. System initialization
    systemClockConfig();        // 72MHz
    hardwareInit();             // GPIO, timers, UART, SPI, ADC
    driverInit();               // Motors, encoders, IMU
    protocolInit();             // Communication
    
    // 2. Create FreeRTOS tasks
    createTasks();              // 4 tasks
    
    // 3. Start scheduler (never returns)
    vTaskStartScheduler();
    
    // Should never reach here
    while(1);
}
```

### orbibot_config.h - Configuration

```c
// include/orbibot_config.h - All robot parameters

// Physical dimensions
#define WHEEL_RADIUS_M          0.050f   // 50mm
#define WHEEL_BASE_M            0.260f   // 260mm
#define TRACK_WIDTH_M           0.360f   // 360mm

// Motor specs
#define MOTOR_GEAR_RATIO        30.0f
#define ENCODER_PPR             1320     // Counts/rev

// Control parameters
#define CONTROL_LOOP_RATE_HZ    100
#define MOTOR_PWM_FREQUENCY_HZ  20000

// PID defaults
#define PID_KP                  0.8f
#define PID_KI                  0.06f
#define PID_KD                  0.5f

// Pin mappings
#define MOTOR1_PWM_PIN          GPIO_Pin_11
#define ENC1_A_PIN              GPIO_Pin_15
// ... more pins ...
```

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Application                                    │
│  • Tasks (control, communication, IMU, monitoring)      │
│  • Protocol handling                                     │
│  • State machines                                        │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Control Algorithms                             │
│  • PID controllers                                       │
│  • Mecanum kinematics                                    │
│  • Odometry calculation                                  │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Device Drivers                                 │
│  • Motor driver (PWM control)                           │
│  • Encoder driver (quadrature reading)                  │
│  • IMU driver (SPI communication)                       │
│  • Battery monitor (ADC)                                │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Hardware Abstraction Layer (HAL)               │
│  • GPIO (pin control)                                   │
│  • Timers (PWM, encoder capture)                        │
│  • USART (serial)                                       │
│  • SPI (IMU)                                            │
│  • ADC (battery)                                        │
├─────────────────────────────────────────────────────────┤
│  Layer 0: Hardware                                       │
│  • STM32F103RCT6 microcontroller                        │
│  • Motors, encoders, IMU, battery                       │
└─────────────────────────────────────────────────────────┘
```

---

## Build System (PlatformIO)

### platformio.ini

```ini
[env:genericSTM32F103RC]
platform = ststm32
board = genericSTM32F103RC
framework = stm32cube

; Build settings
build_flags =
    -D STM32F103xE
    -D USE_STDPERIPH_DRIVER
    -I include
    -O2                    ; Optimization level

; Upload settings
upload_protocol = serial
upload_speed = 115200

; Monitor settings
monitor_speed = 115200
monitor_port = COM3
```

### Build Commands

```bash
# Build firmware
pio run

# Upload to board (requires BOOT0=HIGH)
pio run --target upload

# Monitor serial output
pio device monitor

# Clean build
pio run --target clean
```

---

## File Organization Rules

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| HAL files | `hal_*.c/h` | `hal_gpio.c` |
| Drivers | `*_driver.c/h` | `motor_driver.c` |
| Tasks | `task_*.c/h` | `task_control.c` |
| Control | Descriptive | `pid_controller.c` |

### Include Guards

```c
// include/motor_driver.h
#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H

// ... declarations ...

#endif // MOTOR_DRIVER_H
```

### Header Structure

```c
/**
 * @file motor_driver.h
 * @brief Motor driver interface
 * @author Jewel Nath
 * @date 2025-11-27
 */

#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H

#include <stdint.h>
#include "orbibot_config.h"

// Function declarations
void motor_driver_init(void);
void motor_set_speed(uint8_t motor_id, int16_t speed);
void motor_stop_all(void);

#endif
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Data Flow                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ROS 2 (Raspberry Pi)                                    │
│       ↓ UART (115200 baud)                               │
│  Protocol Parser (task_communication)                    │
│       ↓                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Target Vel  │───→│  Control    │←───│  Encoder    │ │
│  │   (vx,vy,ω) │    │   Task      │    │   Counts    │ │
│  └─────────────┘    │  (100Hz)    │    └─────────────┘ │
│                     │             │                     │
│                     │  ┌───────┐  │                     │
│                     │  │  PID  │  │                     │
│                     │  └───┬───┘  │                     │
│                     └──────┼──────┘                     │
│                            ↓ PWM                        │
│                     ┌─────────────┐                     │
│                     │   Motors    │                     │
│                     └─────────────┘                     │
│                            ↑                            │
│                     ┌─────────────┐                     │
│                     │  IMU Task   │                     │
│                     │   (50Hz)    │←── SPI (ICM-20948)  │
│                     │  Attitude   │                     │
│                     └──────┬──────┘                     │
│                            ↓                            │
│  Protocol Sender ────←─────┴─────←── Odometry           │
│       ↓                                                  │
│  ROS 2 (sensor data)                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Why FreeRTOS?
- Multiple independent tasks with different timing
- Motor control must run at precise 10ms intervals
- Serial communication can be slow and variable

### 2. Why Layered Architecture?
- **Separation of concerns**: Each layer has one job
- **Testability**: Can test layers independently
- **Portability**: Easy to adapt to different hardware

### 3. Why Register-Based HAL?
- Faster than library calls
- Full control over hardware
- Smaller code size

### 4. Why 100Hz Control Rate?
- Fast enough for stable motor control
- Slow enough for CPU to handle other tasks
- Industry standard for mobile robots

---

## Adding New Features

### Example: Add a New Sensor

```c
// 1. Create driver: src/drivers/new_sensor.c
#include "new_sensor.h"

void new_sensor_init(void) {
    // Initialize hardware
}

float new_sensor_read(void) {
    // Read sensor value
    return value;
}

// 2. Create header: include/new_sensor.h
#ifndef NEW_SENSOR_H
#define NEW_SENSOR_H

void new_sensor_init(void);
float new_sensor_read(void);

#endif

// 3. Add to main.c
void driverInit(void) {
    // ... existing drivers ...
    new_sensor_init();
}

// 4. Use in task
void task_monitoring(void *params) {
    while(1) {
        float value = new_sensor_read();
        printf("Sensor: %.2f\n", value);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

---

## Debugging Tips

### Finding Code

| Looking for | Go to |
|-------------|-------|
| Motor control | `src/tasks/task_control.c` |
| PID algorithm | `src/control/pid_controller.c` |
| Serial protocol | `src/communication/protocol.c` |
| Pin mappings | `include/orbibot_config.h` |
| Robot dimensions | `include/orbibot_config.h` |
| IMU driver | `src/drivers/imu_driver.c` |

### Common Files to Edit

| Task | Files |
|------|-------|
| Change PID gains | `include/orbibot_config.h` |
| Add new command | `src/communication/protocol.c` |
| Change pin | `include/orbibot_config.h` + `src/hal/` |
| Add new task | `src/tasks/`, `src/main.c` |

---

## Summary

- **src/**: Source code organized by function
- **include/**: Header files with configuration
- **lib/**: Third-party libraries (FreeRTOS)
- **Layered architecture**: HAL → Drivers → Control → Tasks
- **PlatformIO**: Build system with simple commands
- **Modular design**: Easy to extend and maintain

---

## Next Lesson

[91-main-init.md](91-main-init.md) - Deep dive into main.c initialization

---

*OrbiBot Firmware Study Guide*  
*Part 9 of 10*