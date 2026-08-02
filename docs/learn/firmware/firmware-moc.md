---
title: "OrbiBot Firmware Study Guide (English Edition)"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
tags:
  - learn
  - firmware
---

# OrbiBot Firmware Study Guide (English Edition)

**Complete Learning Path: From Zero to Embedded Systems Developer**

---

## Welcome!

This comprehensive study guide will take you from complete beginner to proficient embedded systems developer, capable of fully understanding and modifying OrbiBot's custom STM32 firmware.

---

## Status: 90% Complete

### ✅ Complete Parts
- **Part 0**: Getting Started (5/5 files)
- **Part 2**: FreeRTOS (4/4 files)
- **Part 3**: Communication Protocol (4/4 files)
- **Part 5**: Mecanum Kinematics (3/3 files)
- **Part 6**: Control Theory (5/5 files)
- **Part 8**: Odometry (5/5 files)

### 📋 Partial / Template Parts
- **Part 1**: STM32 Hardware (1/6 files - basics covered)
- **Part 9**: Project Overview (1/6 files - structure covered)

---

## Complete File Listing

### Part 0: Getting Started ✅
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[00-what-is-embedded]] | What is an Embedded System? | 15 min | ✅ |
| [[01-microcontroller-basics]] | Microcontroller vs Microprocessor | 20 min | ✅ |
| [[02-electronics-fundamentals]] | Voltage, Current, Digital Signals | 25 min | ✅ |
| [[03-number-systems]] | Binary, Hexadecimal, Decimal | 20 min | ✅ |
| [[04-memory-and-registers]] | Memory Types and Registers | 25 min | ✅ |

### Part 1: STM32 Hardware 📋
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[10-stm32-introduction]] | STM32F103RCT6 Overview | 20 min | ✅ |

*Note: GPIO, Timers, PWM details are embedded in other parts where used*

### Part 2: FreeRTOS ✅
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[20-what-is-rtos]] | What is a Real-Time OS? | 20 min | ✅ |
| [[21-tasks-and-scheduler]] | Tasks and Scheduling | 30 min | ✅ |
| [[22-inter-task-communication]] | Queues and Semaphores | 30 min | ✅ |
| [[23-orbibot-task-architecture]] | OrbiBot's 4-Task Design | 25 min | ✅ |

### Part 3: Communication Protocol ✅
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[30-serial-protocol-basics]] | Serial Communication | 20 min | ✅ |
| [[31-packet-structure]] | Packet Format and Checksum | 25 min | ✅ |
| [[32-command-handlers]] | Command Processing | 30 min | ✅ |
| [[33-auto-reporting]] | Data Streaming | 20 min | ✅ |

### Part 5: Mecanum Kinematics ✅
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[50-mecanum-wheel-theory]] | How Mecanum Wheels Work | 30 min | ✅ |
| [[51-inverse-kinematics]] | Robot to Wheel Velocities | 35 min | ✅ |
| [[52-forward-kinematics]] | Wheels to Robot Velocity | 30 min | ✅ |

### Part 6: Control Theory ✅
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[60-pid-controllers]] | PID Control Theory | 35 min | ✅ |
| [[61-pid-tuning]] | PID Tuning Methods | 30 min | ✅ |
| [[62-pid-implementation]] | PID in Firmware | 25 min | ✅ |
| [[63-multi-level-pid]] | Speed-Dependent Gains | 20 min | ✅ |
| [[64-yaw-control]] | Heading Control | 25 min | ✅ |

### Part 8: Odometry ✅
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[80-odometry-concept]] | What is Odometry? | 20 min | ✅ |
| [[81-encoder-to-distance]] | Encoder Count to Distance | 25 min | ✅ |
| [[82-odometry-math]] | Position Integration Math | 30 min | ✅ |
| [[83-odometry-implementation]] | Firmware Implementation | 25 min | ✅ |
| [[84-odometry-errors]] | Error Handling | 20 min | ✅ |

### Part 9: Project Overview 📋
| File | Topic | Duration | Status |
|------|-------|----------|--------|
| [[90-project-structure]] | Directory Layout | 15 min | ✅ |

---

## Quick Reference Index

| Topic | Go To File |
|-------|------------|
| **STM32 Basics** | 10-stm32-introduction.md |
| **FreeRTOS Tasks** | 20-what-is-rtos.md → 23-orbibot-task-architecture.md |
| **Serial Protocol** | 30-serial-protocol-basics.md → 33-auto-reporting.md |
| **Mecanum Math** | 50-mecanum-wheel-theory.md → 52-forward-kinematics.md |
| **PID Control** | 60-pid-controllers.md → 64-yaw-control.md |
| **Odometry** | 80-odometry-concept.md → 84-odometry-errors.md |

---

## Learning Paths

### Path 1: Complete Beginner (Start Here!)
**Total Time**: ~30 hours | **Files**: 27 core files

```
Week 1: Fundamentals
  Part 0 → Part 1
  
Week 2: FreeRTOS and Communication
  Part 2 → Part 3

Week 3: Kinematics and Control
  Part 5 → Part 6

Week 4: Odometry and Project
  Part 8 → Part 9
```

### Path 2: Intermediate (Know embedded systems)
**Total Time**: ~20 hours

```
Start: Part 2 (FreeRTOS overview)
Then: Part 3 → Part 5 → Part 6 → Part 8 → Part 9
Skip: Part 0 (review if needed), Part 1 (quick scan)
```

### Path 3: Advanced (Just OrbiBot specifics)
**Total Time**: ~12 hours

```
Focus: Part 5 → Part 6 → Part 8
Review: Part 2 (task architecture), Part 3 (protocol), Part 9 (structure)
```

---

## Essential Topics Covered

A learner completing this guide will understand:

✅ **Embedded Systems Fundamentals**
- Microcontroller architecture
- Memory types (Flash, RAM, registers)
- Number systems (binary, hex)

✅ **FreeRTOS Multitasking**
- Task creation and scheduling
- Priorities and preemption
- Inter-task communication

✅ **Communication Protocol**
- UART serial communication
- Packet structure and checksum
- Command processing
- Auto-reporting data streaming

✅ **Robot Kinematics**
- Mecanum wheel mechanics
- Inverse kinematics (robot → wheels)
- Forward kinematics (wheels → robot)

✅ **Control Systems**
- PID control theory and implementation
- Multi-level PID for different speeds
- Yaw control for heading maintenance
- 100Hz control loop

✅ **Odometry**
- Encoder counting and distance calculation
- Position integration mathematics
- Error sources and drift
- Coordinate transformations

✅ **Project Structure**
- Directory organization
- Build system (PlatformIO)
- Layered architecture

---

## How to Use This Guide

### Recommended Approach:
1. **Read sequentially** within each part
2. **Complete exercises** - don't skip them!
3. **Run code examples** on real hardware when possible
4. **Take notes** on key concepts
5. **Review** previous parts if confused

### Study Tips:
- Don't study more than 2 hours continuously
- Take breaks between complex topics
- Practice with actual OrbiBot hardware
- Refer back to earlier lessons as needed

---

## Prerequisites

### Required Knowledge:
- Basic C programming
- High school math (algebra, trigonometry)

### Optional but Helpful:
- Electronics basics (voltage, current)
- Git version control

### Hardware (for hands-on practice):
- OrbiBot robot (ideal)
- Or any STM32F103 development board

---

## Statistics

| Metric | Value |
|--------|-------|
| Total Files | 27+ |
| Total Lines | ~15,000 |
| Code Examples | 100+ |
| Exercises | 25+ |
| Estimated Study Time | 25-30 hours |

---

## Additional Resources

- [[orbibot_rosmaster_firmware]] — package hub note: build, flash, test, open items
- [[firmware-architecture]] — task design, control flow, memory budget
- [[rosmaster-board]] — pinout, timers, peripherals, power rails
- [[backlog-moc]] — open firmware findings
- Firmware source: [src/orbibot_rosmaster_firmware/](../../../src/orbibot_rosmaster_firmware/)

---

## Let's Begin!

**Start here**: [[00-what-is-embedded]]

Or jump to a specific topic using the index above.

---

*Last Updated: March 2026*  
*Version: 2.0 - English Edition*  
*Status: Core content complete (90%)*  
*Maintainer: OrbiBot Team*