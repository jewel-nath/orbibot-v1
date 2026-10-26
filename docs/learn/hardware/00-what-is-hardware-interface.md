# 00 - What is a Hardware Interface?

**Understanding how software talks to physical robots**

---

## 🎯 Learning Objectives

After reading this, you will understand:
- What a hardware interface does
- Why we need it for robots
- The role of `orbibot_hardware` in the OrbiBot system
- Basic data flow between software and hardware

---

## 🤔 What Does "Hardware Interface" Mean?

### Real-World Analogy: Computer Graphics

Think about playing a video game on your computer:

```
Game Software → Graphics Driver → GPU Hardware → Monitor Display
     ↑                              ↓
   "Draw this                 Physical pixels
    character"                 light up
```

**The graphics driver is the hardware interface!**

Without it:
- The game can't talk directly to the GPU
- The GPU doesn't understand game commands
- Nothing appears on screen

### The Driver's Job

The graphics driver:
1. **Translates** game commands to GPU instructions
2. **Manages** communication between them
3. **Handles errors** (what if GPU overheats?)
4. **Optimizes** performance

---

## 🎮 Hardware Interface for Robots

### Same Concept, Different Hardware

```
Navigation Software → Hardware Interface → Robot Hardware
       ↑                                         ↓
   "Move forward                          Motors spin
    0.5 m/s"                             Wheels turn
```

**`orbibot_hardware` is OrbiBot's driver!**

### What It Connects

**Software Side (ROS 2):**
- Navigation planning
- SLAM mapping
- Teleoperation (remote control)
- Autonomous decision making

**Hardware Side (Physical Robot):**
- Motors (4 mecanum wheels)
- IMU sensor (orientation)
- Encoders (wheel rotation)
- Battery monitor

---

## 📦 What `orbibot_hardware` Actually Does

### Three Main Jobs

```
┌─────────────────────────────────────────────────────────────┐
│                    orbibot_hardware                          │
├─────────────────────────────────────────────────────────────┤
│  1. RECEIVE COMMANDS                                         │
│     Subscribe to /cmd_vel                                    │
│     "Robot, move at 0.5 m/s forward"                         │
├─────────────────────────────────────────────────────────────┤
│  2. SEND TO HARDWARE                                         │
│     Convert to serial protocol                               │
│     Send to STM32 firmware                                   │
│     Motors spin!                                             │
├─────────────────────────────────────────────────────────────┤
│  3. READ SENSORS                                             │
│     Get IMU data (orientation)                               │
│     Get encoder counts (wheel rotation)                      │
│     Get battery voltage                                      │
│     Publish to ROS topics                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Example

### Scenario: You Press Forward on Controller

**Step-by-Step:**

```
1. YOU press forward on gamepad
        ↓
2. teleop_node receives joystick input
   Calculates: "user wants 0.5 m/s forward"
        ↓
3. teleop_node PUBLISHES to /cmd_vel topic
   Message: Twist(linear.x=0.5)
        ↓
4. hardware_node SUBSCRIBES to /cmd_vel
   Receives the message
        ↓
5. hardware_node CONVERTS command
   ROS units (m/s) → Protocol units (mm/s)
   0.5 m/s → 500 mm/s
        ↓
6. hardware_node SENDS via serial
   Binary packet: [0xFF, 0xFC, 0x08, 0x12, ...]
        ↓
7. STM32 firmware RECEIVES packet
   Parses command
        ↓
8. Firmware CALCULATES wheel speeds
   Mecanum kinematics math
   FL=100, FR=100, BL=100, BR=100 RPM
        ↓
9. Firmware SETS motor PWM
   Motors receive power
        ↓
10. ROBOT MOVES forward at 0.5 m/s!
```

**Total time:** ~5-10 milliseconds (very fast!)

---

## 📊 The Opposite Direction: Sensor Data

### Scenario: Robot is Moving, Navigation Needs to Know Position

```
1. MOTORS are spinning
        ↓
2. ENCODERS measure rotation
   "Motor 1 rotated 100 ticks"
        ↓
3. Firmware READS encoders @ 100Hz
        ↓
4. Firmware CALCULATES odometry
   Position: x=2.5m, y=1.0m
   Heading: 45 degrees
        ↓
5. Firmware SENDS via serial
   Binary packet with position data
        ↓
6. hardware_node RECEIVES packet
   Parses odometry data
        ↓
7. hardware_node PUBLISHES to /odom
   Message: Odometry(x=2.5, y=1.0, theta=0.785)
        ↓
8. navigation_node SUBSCRIBES to /odom
   "Robot is at position (2.5, 1.0)"
        ↓
9. Navigation UPDATES path planning
   "Robot needs to turn left to reach goal"
```

---

## 🏗️ Architecture Overview

### The Three Files

```
orbibot_hardware/
├── hardware_node.py       ← You are here
│   └── Main ROS 2 node
│   └── Handles topics/services
│   └── Manages robot state
│
├── rosmaster_driver.py    ← Lower level
│   └── Serial communication
│   └── Protocol encoding/decoding
│   └── No ROS dependency!
│
└── system_monitor.py      ← Extra monitoring
    └── CPU/RAM/disk usage
    └── Enriches system status
```

### Why Three Files?

**Separation of Concerns** - Each has one job:

| File | Responsibility | Analogy |
|------|---------------|---------|
| `hardware_node.py` | ROS 2 integration | Air traffic controller |
| `rosmaster_driver.py` | Hardware communication | Pilot |
| `system_monitor.py` | System health | Flight engineer |

**Benefits:**
- ✅ Easier to understand
- ✅ Easier to test
- ✅ Can reuse driver without ROS
- ✅ Clear debugging boundaries

---

## 🎓 Key Concepts Summary

### 1. Hardware Interface = Translator
```
Software commands  →  Hardware interface  →  Hardware actions
   (high-level)          (translator)          (low-level)

"Move forward"      →    Serial protocol    →    Motor PWM
```

### 2. Two-Way Communication
```
Software ←→ Hardware Interface ←→ Hardware
    ↑                                ↓
 Commands                        Sensor data
```

### 3. Real-Time Requirements
- Commands must arrive quickly (milliseconds)
- Sensor data must be fresh
- Delays cause unstable robot behavior

### 4. Safety is Critical
- What if communication fails?
- What if battery is low?
- Hardware interface must handle these!

---

## 🧪 Quick Experiment

Try this to see the hardware interface in action:

```bash
# Terminal 1: Launch hardware (if you have robot connected)
ros2 launch orbibot_hardware hardware.launch.py

# Terminal 2: Watch the command topic
ros2 topic echo /cmd_vel

# Terminal 3: Send a test command
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
```

**What you'll see:**
- Terminal 2 shows the Twist message
- Terminal 1 logs show command received
- (If robot connected) motors respond!

**Even without robot:**
You can see the communication flow working.

---

## 📚 Next Steps

Now you understand what a hardware interface does. Next, learn the ROS 2 concepts that make it work:

**→ Continue to:** [01 - ROS 2 Basics for Hardware](01-ros2-basics-for-hardware.md)

---

## 💭 Review Questions

Test your understanding:

1. **Why can't navigation software talk directly to motors?**
   <details>
   <summary>Click for answer</summary>
   They speak different "languages" - navigation uses ROS messages, motors need electrical signals. The hardware interface translates between them.
   </details>

2. **What are the two main directions of data flow?**
   <details>
   <summary>Click for answer</summary>
   1. Commands: Software → Hardware (e.g., /cmd_vel → motors)
   2. Sensor data: Hardware → Software (e.g., encoders → /odom)
   </details>

3. **Why is `rosmaster_driver.py` separate from `hardware_node.py`?**
   <details>
   <summary>Click for answer</summary>
   Separation of concerns - the driver handles low-level serial communication and can be used without ROS. The node handles ROS integration.
   </details>

---

**You're ready for the next lesson! 🚀**