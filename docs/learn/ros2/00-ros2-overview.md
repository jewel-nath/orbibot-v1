---
title: "00 - ROS2 Overview"
type: learn
area: ros2
tags:
  - learn
  - ros2
---

# 00 - ROS2 Overview

**What is ROS2 and why do we use it?**

---

## 🎯 Learning Objectives

- Understand what ROS2 is
- Know the difference between ROS1 and ROS2
- Understand the core concepts: nodes, topics, services
- Know when to use ROS2 vs other systems

---

## 🤖 What is ROS2?

**ROS2** = Robot Operating System 2

Despite the name, ROS2 is **not** an operating system like Windows or Linux. It's a **middleware** - software that helps different parts of a robot talk to each other.

### Real-World Analogy: Restaurant

```
Restaurant = Robot System

Kitchen (Chef) = Node that cooks food
Waiter = Node that takes orders
Cashier = Node that handles payments
Manager = Node that monitors everything

ROS2 = The system that lets them communicate:
- Waiter tells kitchen what to cook (Topics)
- Kitchen asks cashier about prices (Services)
- Manager checks on everything (Monitoring)
```

### Without ROS2

```
hardware_node needs to send data to navigation_node

Option 1: Direct connection
- hardware_node opens TCP socket to navigation_node
- Need to handle: connection failures, data format, rate limiting, etc.
- navigation_node needs to know hardware_node's IP address
- What if navigation_node crashes? Need reconnection logic.

Complex and error-prone!
```

### With ROS2

```python
# hardware_node
self.publisher = self.create_publisher(Odometry, '/odom', 10)
self.publisher.publish(odom_msg)

# navigation_node
self.subscription = self.create_subscription(
    Odometry, '/odom', self.callback, 10)

# ROS2 handles everything else:
# - Discovery (finding each other)
# - Serialization (converting to bytes)
# - Transport (sending over network)
# - Reliability (retry if lost)
# - Lifecycle (handle crashes gracefully)
```

---

## 🏗️ ROS2 Architecture

### Core Concepts

```
┌─────────────────────────────────────────────────────────────┐
│                    ROS2 SYSTEM                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐      Topic       ┌─────────┐                  │
│  │ Node A  │ ───────────────→ │ Node B  │                  │
│  │ (Sensor)│   /sensor_data   │ (Process)│                  │
│  └─────────┘                  └─────────┘                  │
│       │                            │                        │
│       │      Service              │                        │
│       │←──────────────────────────┤                        │
│       │   "Get calibration"       │                        │
│       │                            │                        │
│  ┌─────────┐     Action          ┌─────────┐              │
│  │ Node C  │←────────────────────→│ Node D  │              │
│  │(Planner)│   "Navigate to goal" │ (Robot) │              │
│  └─────────┘                      └─────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Example |
|-----------|---------|---------|
| **Node** | Single purpose program | `hardware_node`, `navigation_node` |
| **Topic** | Data stream (many-to-many) | `/odom`, `/cmd_vel`, `/scan` |
| **Service** | Request-response (one-to-one) | Enable motors, reset odometry |
| **Action** | Long-running task with feedback | Navigate to position |
| **Parameter** | Configuration value | `max_velocity`, `timeout` |

---

## 🔄 ROS1 vs ROS2

| Feature | ROS1 | ROS2 |
|---------|------|------|
| **Middle ware** | Custom (TCPROS/UDPROS) | DDS (standard) |
| **Real-time** | Limited | Native support |
| **Security** | None | Encryption, authentication |
| **Multi-robot** | Hard | Easy |
| **Build tool** | catkin | colcon |
| **Python** | 2.7 | 3.8+ |
| **Lifecycle** | Basic | Managed nodes |

### Why OrbiBot Uses ROS2

```
✅ Modern Python 3 support
✅ Better real-time performance for control loops
✅ DDS handles complex networking automatically
✅ Active development and long-term support
✅ Better integration with modern libraries
```

---

## 📦 ROS2 Distributions

| Distribution | Ubuntu | Status | OrbiBot Support |
|--------------|--------|--------|-----------------|
| Humble | 22.04 | LTS (2027) | ✅ Yes |
| Iron | 22.04 | Standard | ⚠️ Partial |
| Jazzy | 24.04 | Latest LTS | ✅ Primary |
| Rolling | Latest | Development | ❌ No |

**OrbiBot uses: ROS2 Jazzy on Ubuntu 24.04**

---

## 🎯 Core Concepts in Detail

### Nodes

A **node** is a program that does one thing:

```python
# hardware_node: Talks to robot hardware
# navigation_node: Plans paths
# teleop_node: Reads joystick input
```

Nodes can:
- Publish data to topics
- Subscribe to topics
- Provide services
- Call services
- Have parameters

### Topics

A **topic** is a named data stream:

```
Topic: /odom
  Publisher: hardware_node
  Subscribers: navigation_node, slam_node, rviz2

Topic: /cmd_vel
  Publisher: teleop_node, navigation_node
  Subscribers: hardware_node
```

Topics are **many-to-many**:
- One publisher, many subscribers
- Many publishers, one subscriber
- Many publishers, many subscribers

### Services

A **service** is like calling a function:

```python
# Client (navigation_node) calls service
enable_motors(enable=True)

# Server (hardware_node) processes and responds
return success=True, message="Motors enabled"
```

Services are **one-to-one** with guaranteed response.

### Actions

An **action** is for long-running tasks:

```python
# Navigation goal
navigate_to_pose(x=5.0, y=3.0, theta=1.57)

# Server provides:
# - Final result (success/failure)
# - Feedback during execution ("50% complete")
# - Can be cancelled mid-way
```

---

## 🛠️ When to Use ROS2

### Good for ROS2:

```
✅ Multiple sensors and processors
✅ Team of developers
✅ Complex robot with many components
✅ Need visualization and debugging tools
✅ Academic or industrial research
```

### Overkill for:

```
❌ Simple Arduino project with one sensor
❌ Single microcontroller doing one thing
❌ Real-time critical bare-metal system
❌ Learning basic embedded programming
```

---

## 🚀 Your First ROS2 Commands

Try these now (if ROS2 installed):

```bash
# See ROS2 version
ros2 --version

# List available commands
ros2 --help

# Run a demo node (publishes fake data)
ros2 run demo_nodes_py talker

# In another terminal, see the data
ros2 run demo_nodes_py listener

# List running nodes
ros2 node list

# See topics
ros2 topic list
```

---

## 📚 ROS2 Ecosystem

```
ROS2 Core (what you learn here)
    ↓
├─ Navigation (Nav2) - Autonomous movement
├─ Perception - Camera, LIDAR processing
├─ Manipulation - Robot arms
├─ Simulation (Gazebo) - Test without hardware
└─ Visualization (RViz) - See what robot sees

OrbiBot uses:
  - Core: Everything in this guide
  - Nav2: For navigation
  - Gazebo: For simulation
  - RViz: For visualization
```

---

## 🎯 Key Takeaways

1. **ROS2 is middleware** - Helps robot parts communicate
2. **Nodes** - Single-purpose programs
3. **Topics** - Data streams (many-to-many)
4. **Services** - Request-response (one-to-one)
5. **Actions** - Long-running tasks with feedback
6. **ROS2 Jazzy** - What OrbiBot uses on Ubuntu 24.04

---

## 📖 Next Steps

Learn how to set up a workspace:

**→ Continue to:** [[01-workspace-and-packages]]

---

*Last Updated: March 2026*