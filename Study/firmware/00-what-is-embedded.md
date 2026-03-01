# Part 0: What is an Embedded System?

**Duration**: 15 minutes  
**Prerequisites**: None

---

## Learning Objectives

After completing this lesson, you will understand:
- What an embedded system is
- How embedded systems differ from general-purpose computers
- Real-world examples of embedded systems
- Why OrbiBot uses an embedded system

---

## Simple Definition

An **embedded system** is a computer system designed to perform a specific, dedicated task.

### Comparison

| General-Purpose Computer | Embedded System |
|-------------------------|-----------------|
| PC, laptop, smartphone | Washing machine controller, robot firmware |
| Many different tasks | One specific task |
| User runs various programs | Runs one program continuously |
| Flexible and complex | Optimized and efficient |

### Visual Analogy

```
General-Purpose (PC):
  Can do: Gaming + Browsing + Coding + Video editing
  Like: A Swiss Army knife - many tools, not specialized

Embedded System:
  Does: Only motor control, 100 times per second
  Like: A scalpel - one purpose, highly optimized
```

---

## Embedded Systems Around You

### Home Appliances
- **Washing machine**: Controls wash cycles, water temperature, spin speed
- **Microwave**: Manages cooking time and power level
- **Air conditioner**: Maintains temperature using sensors
- **Smart thermostat**: Learns schedules, controls HVAC

### Automotive
- **Engine control unit (ECU)**: Optimizes fuel injection and ignition timing
- **Anti-lock braking system (ABS)**: Prevents wheel lock during braking
- **Airbag controller**: Detects crashes and deploys airbags in milliseconds

### Medical
- **Pacemaker**: Regulates heart rhythm
- **Insulin pump**: Delivers precise doses automatically
- **MRI machine**: Controls powerful magnets and sensors

---

## OrbiBot's Embedded System

OrbiBot uses a **dual-computer architecture**:

```
┌─────────────────────────────────────────┐
│  Raspberry Pi 5                         │
│  • Linux operating system               │
│  • ROS 2 navigation and planning        │
│  • SLAM mapping                         │
│  • General-purpose computing            │
└───────────────┬─────────────────────────┘
                │ USB Serial (UART)
                ▼
┌─────────────────────────────────────────┐
│  STM32F103 Microcontroller              │
│  • Real-time motor control (100Hz)      │
│  • Encoder reading                      │
│  • IMU sensor processing (50Hz)         │
│  • Odometry calculation                 │
│  • Embedded system (this firmware!)     │
└─────────────────────────────────────────┘
```

### Why Two Computers?

**Raspberry Pi alone would fail because:**
- Linux is not real-time (timing is unpredictable)
- Motor control requires precise 10ms intervals
- If a process uses CPU, motors could stutter or stop

**STM32 alone would fail because:**
- 48KB RAM is too small for ROS 2
- Cannot run SLAM or navigation algorithms
- No WiFi, Bluetooth, or high-level networking

**Together they provide:**
- Pi: High-level intelligence (planning, perception)
- STM32: Real-time control (motors, sensors)
- Best of both worlds!

---

## Key Characteristics of Embedded Systems

### 1. Dedicated Function
```c
// OrbiBot firmware does ONE thing:
while(1) {
    read_sensors();      // Every 10ms
    calculate_pid();     // Motor control
    update_motors();     // Apply control
}
```

### 2. Resource Constraints
```
STM32F103RCT6 Resources:
- 72 MHz CPU (modest speed)
- 48 KB RAM (small)
- 256 KB Flash (limited storage)

The firmware fits in 38 KB - highly optimized!
```

### 3. Real-Time Requirements
```
Control loop MUST run every 10ms (100Hz):
  ✓ 10.0ms - good
  ✓ 10.1ms - acceptable
  ✗ 15.0ms - robot becomes unstable!
  ✗ 50.0ms - robot crashes!

This is why we use a dedicated microcontroller.
```

### 4. Reliability
- Runs for days without crashing
- Handles errors gracefully
- Watchdog timer resets if stuck

---

## Exercise: Identify Embedded Systems

Look around your room. Which devices contain embedded systems?

**Examples to consider:**
1. Your phone (has multiple embedded processors!)
2. TV remote control
3. Digital watch
4. Kitchen appliances
5. Game controller

**Questions:**
1. What specific task does each perform?
2. Why couldn't a general computer do this?
3. What would happen if it failed?

---

## Summary

- **Embedded system** = Computer for a specific task
- **Different from PCs** = Optimized, not flexible
- **Everywhere** = Appliances, cars, medical devices, robots
- **OrbiBot uses** = STM32 for real-time control + Raspberry Pi for intelligence

---

## Next Lesson

[01-microcontroller-basics.md](01-microcontroller-basics.md) - Learn about microcontrollers vs microprocessors

---

*OrbiBot Firmware Study Guide*  
*Part 0 of 10*