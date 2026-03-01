# Part 2: What is a Real-Time Operating System?

**Duration**: 20 minutes  
**Prerequisites**: [03-number-systems.md](03-number-systems.md)

---

## Learning Objectives

After this lesson, you will understand:
- What an RTOS is and why we use it
- Difference between bare-metal and RTOS
- FreeRTOS introduction
- When to use (and not use) an RTOS
- OrbiBot's 4-task architecture overview

---

## What is an RTOS?

**RTOS** = Real-Time Operating System

### Simple Definition

An OS that guarantees tasks complete within specific time deadlines.

### Real-Time vs Non-Real-Time

| System | Timing Guarantee | Example |
|--------|------------------|---------|
| **Hard Real-Time** | Must meet deadline, failure = disaster | Airbag deployment, pacemaker |
| **Soft Real-Time** | Should meet deadline, failure = degraded | Video streaming, game frame rate |
| **Non-Real-Time** | No timing guarantee | Email, web browsing |

```
OrbiBot Motor Control: HARD REAL-TIME
  - MUST run every 10ms (100Hz)
  - Missing deadline = unstable robot, possible crash
  - This is why we use FreeRTOS!

ROS 2 Navigation: SOFT REAL-TIME
  - Should plan path in 100ms
  - Delay = slower response, but robot still safe
```

---

## Bare-Metal vs RTOS

### Bare-Metal Programming (Without RTOS)

```c
// Sequential execution - one thing at a time
void main(void) {
    while(1) {
        read_sensors();      // 2ms
        // Motor control waits!
        
        motor_control();     // 5ms (MUST run every 10ms)
        // But what if sensors took longer?
        
        process_serial();    // Variable time (1-50ms)
        // Serial can delay motor control!
        
        check_battery();     // 1ms
    }
}

PROBLEM: If serial takes 50ms, motor control is delayed!
         Robot becomes unstable and may crash.
```

### RTOS Programming (With FreeRTOS)

```c
// Parallel execution - multiple tasks running "simultaneously"

// Task 1: Motor Control (HIGHEST PRIORITY)
void task_control(void *params) {
    while(1) {
        motor_control();                    // Run every 10ms
        vTaskDelay(pdMS_TO_TICKS(10));      // Wait, let others run
    }
}

// Task 2: Serial Communication
void task_communication(void *params) {
    while(1) {
        process_serial();                   // When data arrives
        vTaskDelay(pdMS_TO_TICKS(1));       // Check frequently
    }
}

// Task 3: IMU Reading
void task_imu(void *params) {
    while(1) {
        read_imu();                         // Every 20ms
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

// Task 4: Monitoring (LOWEST PRIORITY)
void task_monitoring(void *params) {
    while(1) {
        check_battery();                    // Every 1 second
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

BENEFIT: Motor control ALWAYS runs every 10ms, regardless of what other tasks are doing!
```

### Visual Comparison

```
BARE-METAL (Sequential):
Time →
     ├────────────┬────────┬──────────────┬────┤
Task: Sensors    Motor    Serial         Battery
      (2ms)      (5ms)    (50ms!)        (1ms)
                 ↑
                 Delayed by slow serial!

Total loop: 58ms → Motor missed multiple deadlines!


RTOS (Parallel with Priorities):
Time →
     ├─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┤
Motor: █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █ █  (every 10ms)
       (P10 - Highest, preempts others)

Serial:  ░░░░░░████░░░░░░████░░░░░░░░░░░░░░░░░  (when possible)
          (P9 - Lower, runs in gaps)

IMU:     ░░░░░░░░░░░░████░░░░░░░░░░░░████░░░░░  (every 20ms)
          (P8 - Lower)

Battery: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░███  (every 1000ms)
          (P5 - Lowest, runs when idle)

Legend: █ = Running,  ░ = Waiting

Motor ALWAYS runs on time - other tasks fill the gaps!
```

---

## FreeRTOS Introduction

### What is FreeRTOS?

- **Free**: Open source (MIT license)
- **RTOS**: Real-time operating system
- **Small footprint**: ~10KB Flash, ~1-2KB RAM
- **Popular**: Used in millions of devices worldwide
- **Well-documented**: Extensive documentation and community

### FreeRTOS in OrbiBot

```
OrbiBot Configuration:
- Version: FreeRTOS v10.2.1
- Kernel: Preemptive scheduler
- Tick rate: 1000Hz (1ms resolution)
- Heap size: 20KB
- Number of tasks: 4
```

### Memory Footprint

| Component | Size |
|-----------|------|
| FreeRTOS Kernel | ~10KB Flash |
| Task Stacks (4 tasks) | ~6KB RAM |
| Queues/Semaphores | ~200 bytes |
| **Total** | **~16KB** |
| STM32 Available | 256KB Flash, 48KB RAM |
| **Remaining for application** | **Plenty!** |

---

## When to Use RTOS

### ✅ Use RTOS When:

1. **Multiple independent tasks**
   - Motor control + sensor reading + communication
   - Each task has different timing requirements

2. **Timing-critical operations**
   - Must run at precise intervals (e.g., 100Hz control loop)
   - Cannot tolerate unpredictable delays

3. **Complex projects**
   - Robot, drone, IoT devices
   - Need modular, maintainable code

4. **Async events**
   - Serial data arrives unpredictably
   - Button presses, interrupts

### ❌ Don't Use RTOS When:

1. **Simple projects**
   - LED blink, basic sensor reading
   - Single task, no timing constraints

2. **Very limited memory**
   - Less than 8KB RAM
   - Every byte matters

3. **Learning embedded basics**
   - Learn bare-metal first (timers, interrupts, GPIO)
   - Then move to RTOS

4. **Single task applications**
   - Only one thing to do
   - No need for multitasking

---

## OrbiBot's 4-Task Architecture

```
┌─────────────────────────────────────────────────────┐
│              FreeRTOS Scheduler                     │
│         (Decides which task runs when)              │
└──────────┬────────────┬──────────┬──────────────────┘
           │            │          │            │
    ┌──────▼──────┐ ┌───▼────┐ ┌──▼──────┐ ┌──▼────────┐
    │   Control   │ │  Comm  │ │   IMU   │ │ Monitoring│
    │  (P10,10ms) │ │(P9,1ms)│ │(P8,20ms)│ │ (P5,1s)   │
    └──────┬──────┘ └───┬────┘ └──┬──────┘ └──┬────────┘
           │            │          │            │
    ┌──────▼────────────▼──────────▼────────────▼──────┐
    │              Hardware Abstraction Layer          │
    │         (GPIO, Timers, SPI, UART, ADC)           │
    └──────────────────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │  STM32F103RCT6  │
                  │   (72MHz MCU)   │
                  └─────────────────┘
```

### Task Summary

| Task | Priority | Period | Purpose |
|------|----------|--------|---------|
| Control | 10 (Highest) | 10ms | Motor PID, odometry |
| Communication | 9 | 1ms | Serial RX/TX with ROS |
| IMU | 8 | 20ms | Read ICM-20948 sensor |
| Monitoring | 5 (Lowest) | 1000ms | Battery, diagnostics |

### Why This Priority Order?

```
Priority 10: Control Task
  - Motor control is SAFETY CRITICAL
  - Must run every 10ms - no exceptions
  - Preempts all other tasks

Priority 9: Communication
  - ROS commands need quick response
  - But can wait a few ms if motor control running

Priority 8: IMU
  - Sensor reading important but slower (50Hz)
  - Can tolerate small delays

Priority 5: Monitoring
  - Battery check not time-critical
  - Runs when CPU is idle
```

---

## Key RTOS Concepts (Preview)

We'll cover these in detail in upcoming lessons:

1. **Tasks**: Independent execution units
2. **Scheduler**: Decides which task runs
3. **Priorities**: Higher number = more important
4. **Delays**: vTaskDelay, vTaskDelayUntil
5. **Queues**: Pass data between tasks
6. **Semaphores**: Signal between tasks
7. **Mutexes**: Protect shared resources
8. **Critical Sections**: Disable interrupts briefly

---

## Exercise: Think About It

**Question**: Why doesn't OrbiBot run everything on the Raspberry Pi? Why do we need the STM32 with FreeRTOS?

**Think about it, then check the answer:**

<details>
<summary>Click for answer</summary>

```
Raspberry Pi (Linux) is NOT real-time:
  - Linux scheduler is unpredictable
  - A process can delay motor control by 50-100ms
  - Robot would be unstable and crash

STM32 with FreeRTOS IS real-time:
  - Guaranteed 10ms motor control (hard real-time)
  - Predictable, reliable timing
  - Dedicated to robot control

Best of both:
  - Pi: High-level intelligence (navigation, AI)
  - STM32: Real-time control (motors, sensors)
```

</details>

---

## Summary

- **RTOS** = Operating system with timing guarantees
- **FreeRTOS** = Small, popular, open-source RTOS
- **OrbiBot uses** = 4 tasks with different priorities
- **Benefit** = Motor control always runs on time
- **Trade-off** = Slightly more memory, more complex

---

## Next Lesson

[21-tasks-and-scheduler.md](21-tasks-and-scheduler.md) - Creating tasks and understanding the scheduler

---

*OrbiBot Firmware Study Guide*  
*Part 2 of 10*