# Part 2: OrbiBot Task Architecture

> **Note:** this lesson was written before 2026-04-28, when OrbiBot stopped using the ICM-20948's magnetometer. The IMU task below still shows the magnetometer and a gyro/magnetometer complementary filter. Today the IMU sends gyro and accelerometer only, in a 12-byte packet, and the yaw comes from the gyro alone.

**Duration**: 25 minutes  
**Prerequisites**: [Part 2: Tasks and Scheduler](21-tasks-and-scheduler.md), [Part 2: Inter-Task Communication](22-inter-task-communication.md)

---

## Learning Objectives

After this lesson, you will understand:
- OrbiBot's 4-task design
- What each task does and why
- How tasks communicate
- The data flow through the system
- Timing and priorities of each task

---

## Overview

OrbiBot uses **4 FreeRTOS tasks** to handle different responsibilities:

```
┌─────────────────────────────────────────────────────────┐
│                    OrbiBot Firmware                      │
│              FreeRTOS Preemptive Scheduler               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────┐    Priority 10 (Highest)          │
│  │  Control Task   │    100Hz (10ms)                    │
│  │  • Motor PID    │    • Motor control                 │
│  │  • Odometry     │    • Real-time critical            │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐    Priority 9                      │
│  │  Communication  │    1000Hz (1ms)                    │
│  │  • Serial RX    │    • ROS commands                  │
│  │  • Serial TX    │    • Data streaming                │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐    Priority 8                      │
│  │   IMU Task      │    50Hz (20ms)                     │
│  │  • Read sensor  │    • Attitude estimation           │
│  │  • Calibration  │    • Sensor fusion                 │
│  └────────┬────────┘                                     │
│           │                                              │
│  ┌────────▼────────┐    Priority 5 (Lowest)             │
│  │  Monitoring     │    1Hz (1000ms)                    │
│  │  • Battery      │    • Diagnostics                   │
│  │  • Watchdog     │    • Health checks                 │
│  └─────────────────┘                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Task 1: Control Task

### Purpose
The most important task - keeps the robot stable and moving correctly.

### Responsibilities
1. **Read encoders** - Get wheel positions
2. **Calculate velocity** - From encoder deltas
3. **Update odometry** - Track robot position
4. **PID control** - Calculate motor outputs
5. **Safety checks** - Command timeout, limits

### Specifications

| Property | Value |
|----------|-------|
| **Priority** | 10 (Highest) |
| **Period** | 10ms (100Hz) |
| **Stack** | 512 words (2KB) |
| **Deadline** | Hard real-time |

### Code Structure

```c
// From: src/tasks/task_control.c

void task_control(void *params)
{
    // Initialize timing
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(10);  // 10ms
    
    // Initialize PID controllers
    for (int i = 0; i < 4; i++) {
        pid_init(&pid_motor[i], PID_KP, PID_KI, PID_KD, MAX_OUTPUT);
    }
    
    // Main loop
    for (;;)
    {
        // 1. Read encoders (current wheel positions)
        int16_t delta[4];
        for (int i = 0; i < 4; i++) {
            delta[i] = encoder_read_delta(i);
        }
        
        // 2. Calculate wheel speeds (m/s)
        float wheel_speeds[4];
        for (int i = 0; i < 4; i++) {
            wheel_speeds[i] = delta[i] * ENCODER_TO_MPS;
        }
        
        // 3. Forward kinematics: wheels → robot velocity
        robot_velocity_t robot_vel;
        mecanum_forward_kinematics(&wheel_speeds, &robot_vel);
        
        // 4. Update odometry (position tracking)
        odometry_update(&odom, &wheel_speeds, dt);
        
        // 5. Get target velocity (from communication task)
        robot_velocity_t target;
        taskENTER_CRITICAL();
        target = target_velocity;  // Shared variable
        taskEXIT_CRITICAL();
        
        // 6. Inverse kinematics: robot → wheel targets
        wheel_velocity_t target_wheels;
        mecanum_inverse_kinematics(&target, &target_wheels);
        
        // 7. PID control for each motor
        for (int i = 0; i < 4; i++) {
            pid_set_target(&pid_motor[i], target_wheels[i]);
            float output = pid_calculate(&pid_motor[i], wheel_speeds[i]);
            motor_set_speed(i, output);
        }
        
        // 8. Wait for next period (NO DRIFT!)
        vTaskDelayUntil(&last_wake_time, period);
    }
}
```

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  Control Task Data Flow                                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  INPUTS:                                                 │
│  • Encoder counts ← Hardware (TIM2-5)                   │
│  • Target velocity ← Communication task (shared var)    │
│                                                          │
│  PROCESSING:                                             │
│  • Calculate wheel speeds                                │
│  • Forward kinematics → robot velocity                   │
│  • Odometry integration → position                       │
│  • Inverse kinematics → wheel targets                    │
│  • PID control → motor outputs                           │
│                                                          │
│  OUTPUTS:                                                │
│  • PWM values → Motor drivers (TIM1, TIM8)              │
│  • Odometry data → Communication task (shared)          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Task 2: Communication Task

### Purpose
Bridge between ROS 2 (Raspberry Pi) and firmware (STM32).

### Responsibilities
1. **Receive commands** - Parse serial packets from Pi
2. **Send data** - Stream sensor data to Pi
3. **Protocol handling** - Checksum, state machine
4. **Command dispatch** - Execute received commands

### Specifications

| Property | Value |
|----------|-------|
| **Priority** | 9 |
| **Period** | 1ms (1000Hz) |
| **Stack** | 512 words (2KB) |
| **Deadline** | Soft real-time |

### Auto-Report Cycle

When enabled, sends data in 50ms cycle:

```
Time (ms) →
0          10         20         30         40         50
├──────────┼──────────┼──────────┼──────────┼──────────┤
│  Speed   │          │  IMU Raw │          │ Encoders │
│  + Bat   │          │          │          │          │
├──────────┼──────────┼──────────┼──────────┼──────────┤
                     │  IMU Attitude  │
                     │   (roll/pitch/yaw)  │
                     └─────────────────────┘
                     
Every 50ms cycle:
  0ms:  Speed + Battery
  10ms: (gap)
  20ms: IMU Raw data
  30ms: (gap)
  40ms: Encoder counts
  50ms: Start of next cycle
```

### Code Structure

```c
// From: src/tasks/task_communication.c

void task_communication(void *params)
{
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(1);  // 1ms
    
    uint16_t report_counter = 0;
    
    for (;;)
    {
        // 1. Check for incoming commands
        if (protocol_command_ready()) {
            protocol_parse_command();  // Parse and execute
        }
        
        // 2. Auto-report data (if enabled)
        if (auto_report_enabled) {
            switch (report_counter) {
                case 1:   // 1ms
                    send_speed_and_battery();
                    break;
                    
                case 11:  // 11ms
                    send_imu_raw_data();
                    break;
                    
                case 21:  // 21ms
                    send_imu_attitude();
                    break;
                    
                case 31:  // 31ms
                    send_encoder_counts();
                    break;
                    
                case 41:  // 41ms
                    send_odometry();
                    break;
            }
            
            report_counter++;
            if (report_counter > 50) {
                report_counter = 0;  // Reset every 50ms
            }
        }
        
        vTaskDelayUntil(&last_wake_time, period);
    }
}
```

### Command Processing

```c
// Parse and execute received commands
void protocol_parse_command(void)
{
    uint8_t *packet = get_received_packet();
    uint8_t function = packet[3];  // Function code
    
    switch (function) {
        case FUNC_MOTION:
            // Set target velocity
            int16_t vx = (packet[5] << 8) | packet[4];
            int16_t vy = (packet[7] << 8) | packet[6];
            int16_t vz = (packet[9] << 8) | packet[8];
            
            // Update shared variable (protected by critical section)
            taskENTER_CRITICAL();
            target_velocity.vx = vx / 1000.0f;  // mm/s to m/s
            target_velocity.vy = vy / 1000.0f;
            target_velocity.omega = vz / 1000.0f;  // mrad/s to rad/s
            taskEXIT_CRITICAL();
            break;
            
        case FUNC_AUTO_REPORT:
            auto_report_enabled = packet[4];  // Enable/disable
            break;
            
        case FUNC_RESET_ODOM:
            odometry_reset();
            break;
            
        case FUNC_SET_MOTOR_PID:
            // Update PID gains
            update_pid_gains(packet);
            break;
            
        // ... more commands ...
    }
}
```

---

## Task 3: IMU Task

### Purpose
Read and process IMU sensor data for orientation estimation.

### Responsibilities
1. **Read ICM-20948** - Via SPI bus
2. **Calibration** - Gyro bias removal
3. **Attitude estimation** - Roll, pitch, yaw
4. **Sensor fusion** - Complementary filter

### Specifications

| Property | Value |
|----------|-------|
| **Priority** | 8 |
| **Period** | 20ms (50Hz) |
| **Stack** | 256 words (1KB) |
| **Deadline** | Soft real-time |

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  IMU Task Data Flow                                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  HARDWARE:                                               │
│  ICM-20948 ← SPI2 (PB13-PB15)                           │
│                                                          │
│  READ:                                                   │
│  • Accelerometer (X, Y, Z)                               │
│  • Gyroscope (X, Y, Z)                                   │
│  • Magnetometer (X, Y, Z) - via I2C master              │
│                                                          │
│  PROCESSING:                                             │
│  • Apply calibration (bias removal)                      │
│  • Calculate roll/pitch from accelerometer               │
│  • Integrate gyro for yaw                                │
│  • Complementary filter (98% gyro, 2% mag)              │
│                                                          │
│  OUTPUT:                                                 │
│  • Attitude angles → Communication task                 │
│  • Raw sensor data → Communication task                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Code Structure

```c
// From: src/tasks/task_imu.c

void task_imu(void *params)
{
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(20);  // 20ms
    
    // Initialize attitude
    float roll = 0, pitch = 0, yaw = 0;
    
    for (;;)
    {
        // 1. Read calibrated IMU data
        imu_data_t data;
        imu_read_calibrated(&data);
        
        // 2. Calculate roll and pitch from accelerometer
        // roll = atan2(ay, az)
        roll = atan2f(data.accel_y, data.accel_z);
        
        // pitch = atan2(-ax, sqrt(ay² + az²))
        pitch = atan2f(-data.accel_x, 
                       sqrtf(data.accel_y * data.accel_y + 
                             data.accel_z * data.accel_z));
        
        // 3. Integrate gyro for yaw (with drift correction)
        // Gyro integration: yaw += gyro_z * dt
        yaw += data.gyro_z * 0.02f;  // 20ms = 0.02s
        
        // 4. Magnetometer drift correction
        if (data.mag_x != 0 || data.mag_y != 0) {
            float mag_yaw = atan2f(-data.mag_y, data.mag_x);
            
            // Complementary filter: 98% gyro, 2% magnetometer
            float diff = mag_yaw - yaw;
            // Normalize diff to -PI to PI...
            yaw += 0.02f * diff;  // Slow correction
        }
        
        // 5. Store in global variables (protected)
        taskENTER_CRITICAL();
        imu_attitude.roll = roll;
        imu_attitude.pitch = pitch;
        imu_attitude.yaw = yaw;
        taskEXIT_CRITICAL();
        
        vTaskDelayUntil(&last_wake_time, period);
    }
}
```

---

## Task 4: Monitoring Task

### Purpose
System health monitoring and diagnostics.

### Responsibilities
1. **Battery monitoring** - Voltage measurement
2. **Watchdog feeding** - Prevent system reset
3. **Status LED** - Visual system health
4. **Diagnostics** - Print system status

### Specifications

| Property | Value |
|----------|-------|
| **Priority** | 5 (Lowest) |
| **Period** | 1000ms (1Hz) |
| **Stack** | 256 words (1KB) |
| **Deadline** | Non-critical |

### Code Structure

```c
// From: src/tasks/task_monitoring.c

void task_monitoring(void *params)
{
    for (;;)
    {
        // 1. Read battery voltage (ADC)
        uint16_t adc_value = adc_read_battery();
        float voltage = adc_to_voltage(adc_value);
        
        // 2. Check for warnings
        if (voltage < BATTERY_LOW_VOLTAGE) {
            printf("WARNING: Low battery! %.2fV\n", voltage);
            set_warning_led(1);
        }
        
        // 3. Feed watchdog (prevent system reset)
        watchdog_feed();
        
        // 4. Toggle status LED (show system is alive)
        toggle_status_led();
        
        // 5. Print diagnostics (every 5 seconds)
        static int count = 0;
        if (++count >= 5) {
            count = 0;
            print_diagnostics();
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000));  // 1 second
    }
}

void print_diagnostics(void)
{
    printf("\n--- System Diagnostics ---\n");
    printf("Uptime: %lu seconds\n", get_uptime());
    printf("Battery: %.2fV\n", battery_voltage);
    printf("Free heap: %u bytes\n", xPortGetFreeHeapSize());
    printf("CPU usage: %u%%\n", get_cpu_usage());
    printf("--------------------------\n");
}
```

---

## Inter-Task Communication

### Shared Variables

Tasks communicate through shared variables protected by critical sections:

```c
// Shared variables (defined in main.c or appropriate module)

// Target velocity (written by Comm, read by Control)
volatile robot_velocity_t target_velocity;

// Current odometry (written by Control, read by Comm)
volatile odometry_t current_odometry;

// IMU attitude (written by IMU, read by Comm)
volatile imu_attitude_t imu_attitude;

// Battery voltage (written by Monitor, read by Comm)
volatile float battery_voltage;
```

### Critical Section Protection

```c
// Writing to shared variable (Communication task)
void set_target_velocity(float vx, float vy, float omega)
{
    taskENTER_CRITICAL();
    target_velocity.vx = vx;
    target_velocity.vy = vy;
    target_velocity.omega = omega;
    taskEXIT_CRITICAL();
}

// Reading from shared variable (Control task)
void get_target_velocity(robot_velocity_t *out)
{
    taskENTER_CRITICAL();
    out->vx = target_velocity.vx;
    out->vy = target_velocity.vy;
    out->omega = target_velocity.omega;
    taskEXIT_CRITICAL();
}
```

---

## System Timing Diagram

```
Time (ms) →
0    10   20   30   40   50   60   70   80   90   100
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤

Control (10ms):
████      ████      ████      ████      ████
Motor PID runs every 10ms without fail!

Comm (1ms):
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Runs continuously, checking serial data

IMU (20ms):
          ████                ████
          Sensor reading every 20ms

Monitor (1000ms):
████
Only runs once per second (low priority)

Legend:
████ = Task running (CPU busy)
     = Task waiting (CPU available to lower priority)
```

---

## Task Creation Summary

```c
// From: src/main.c

void create_tasks(void)
{
    // Task 1: Control (Highest priority, 100Hz)
    xTaskCreate(
        task_control,
        "Control",
        512,           // 2KB stack
        NULL,
        10,            // Priority 10
        NULL
    );
    
    // Task 2: Communication (Priority 9, 1000Hz)
    xTaskCreate(
        task_communication,
        "Comm",
        512,           // 2KB stack
        NULL,
        9,             // Priority 9
        NULL
    );
    
    // Task 3: IMU (Priority 8, 50Hz)
    xTaskCreate(
        task_imu,
        "IMU",
        256,           // 1KB stack
        NULL,
        8,             // Priority 8
        NULL
    );
    
    // Task 4: Monitoring (Lowest priority, 1Hz)
    xTaskCreate(
        task_monitoring,
        "Monitor",
        256,           // 1KB stack
        NULL,
        5,             // Priority 5
        NULL
    );
}
```

---

## Summary

| Task | Priority | Rate | Purpose | Stack |
|------|----------|------|---------|-------|
| Control | 10 | 100Hz | Motor PID, odometry | 2KB |
| Communication | 9 | 1000Hz | Serial protocol | 2KB |
| IMU | 8 | 50Hz | Sensor reading | 1KB |
| Monitoring | 5 | 1Hz | Health checks | 1KB |

**Total stack usage**: 6KB  
**FreeRTOS heap**: 20KB  
**Remaining for queues/heap**: ~13KB

---

## Next Lesson

[Part 3: Serial Communication Protocol](30-serial-protocol-basics.md) - Communication protocol overview

---

*OrbiBot Firmware Study Guide*  
*Part 2 of 10*