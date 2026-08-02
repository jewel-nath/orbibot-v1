---
title: "01 - ROS 2 Basics for Hardware"
type: learn
area: hardware
package: orbibot_hardware
tags:
  - learn
  - hardware
---

# 01 - ROS 2 Basics for Hardware

**Essential ROS 2 concepts explained simply**

---

## 🎯 Learning Objectives

After reading this, you will understand:
- What a ROS 2 Node is
- How Topics work (publish/subscribe)
- What Services are and when to use them
- How Timers enable periodic tasks
- The message types used in `orbibot_hardware`

---

## 🤖 What is a Node?

### Simple Definition
A **Node** is a program that does one specific job in the robot system.

### Real-World Analogy: Restaurant

```
Restaurant System (Robot System)
├── Chef Node        → Cooks food
├── Waiter Node      → Takes orders, serves food  
├── Cashier Node     → Handles payments
└── Manager Node     → Monitors everything

Each node has ONE job, but they work together!
```

### OrbiBot Hardware Nodes

```
OrbiBot System
├── hardware_node        ← WE ARE HERE
│   └── Talks to robot hardware
│
├── system_monitor
│   └── Monitors computer resources
│
├── control_manager (different package)
│   └── Calculates position from sensor data
│
└── teleop_node (different package)
    └── Reads gamepad, sends commands
```

### Node Characteristics

| Property | Description | Example |
|----------|-------------|---------|
| **Name** | Unique identifier | `orbibot_hardware_node` |
| **Job** | Single responsibility | Handle hardware communication |
| **Communication** | Topics, services, actions | Publishes `/odom`, subscribes `/cmd_vel` |
| **Lifecycle** | Starts, runs, stops | Launch → Spin → Shutdown |

### Code Example: Creating a Node

```python
import rclpy
from rclpy.node import Node

class OrbiBotHardwareNode(Node):  # Inherits from Node
    def __init__(self):
        # Node name = 'orbibot_hardware_node'
        super().__init__('orbibot_hardware_node')
        
        # This node is now registered with ROS 2!
        self.get_logger().info("Node started!")
```

**Key Points:**
- Class inherits from `Node`
- `super().__init__()` sets the node name
- Node name appears in logs, debugging tools

---

## 📡 Topics: The Communication Channels

### What is a Topic?

A **Topic** is like a **radio channel** where nodes broadcast messages.

### Analogy: YouTube Channel

```
YouTube Analogy:
┌────────────────────────────────────────┐
│ Channel Name: /cmd_vel                 │
├────────────────────────────────────────┤
│ Publisher: teleop_node                 │
│   "I want to move 0.5 m/s forward"     │
├────────────────────────────────────────┤
│ Subscribers:                           │
│   - hardware_node (acts on command)    │
│   - control_manager (logs commands)    │
│   - safety_monitor (checks limits)     │
└────────────────────────────────────────┘

One publisher, multiple subscribers!
```

### Topic Characteristics

| Property | Meaning | Example |
|----------|---------|---------|
| **Name** | Channel identifier | `/cmd_vel`, `/odom` |
| **Message Type** | Data format | `Twist`, `Odometry` |
| **Publisher** | Sends data | `hardware_node` (for sensors) |
| **Subscriber** | Receives data | `control_manager` |
| **QoS** | Delivery reliability | Reliable, Best Effort |

### Two Key Topics in OrbiBot Hardware

#### 1. /cmd_vel (Commands TO Robot)

```
Direction: teleop_node → hardware_node

Message Type: geometry_msgs/Twist

Data Structure:
Twist:
  linear:
    x: 0.5   # forward/back (m/s)
    y: 0.0   # left/right (m/s) - for mecanum!
    z: 0.0   # up/down (not used for ground robots)
  angular:
    x: 0.0   # roll (not used)
    y: 0.0   # pitch (not used)
    z: 0.1   # yaw - rotation (rad/s)

Example Commands:
- Forward:  linear.x = 0.5
- Left:     linear.y = 0.3
- Rotate:   angular.z = 0.5
- Stop:     all zeros
```

#### 2. /odom (Position FROM Robot)

```
Direction: hardware_node → navigation

Message Type: nav_msgs/Odometry

Data Structure:
Odometry:
  header:
    stamp: timestamp
    frame_id: 'odom'
  
  pose:                    # WHERE am I?
    position:
      x: 2.5    # meters east of start
      y: 1.0    # meters north of start
      z: 0.0    # always 0 for ground robot
    orientation:          # WHICH way am I facing?
      x: 0.0    # quaternion component
      y: 0.0    # quaternion component
      z: 0.383  # quaternion component
      w: 0.924  # quaternion component
  
  twist:                  # HOW FAST am I moving?
    linear:
      x: 0.5    # m/s forward
    angular:
      z: 0.1    # rad/s rotation

This tells navigation: "I'm at position (2.5, 1.0), 
facing 45 degrees, moving 0.5 m/s forward"
```

### Creating a Publisher (Code)

```python
from sensor_msgs.msg import Imu

class OrbiBotHardwareNode(Node):
    def __init__(self):
        super().__init__('orbibot_hardware_node')
        
        # Create publisher
        self.imu_pub = self.create_publisher(
            Imu,           # Message type
            '/imu/data',   # Topic name
            10             # Queue size (buffer last 10 messages)
        )
    
    def publish_imu(self):
        msg = Imu()
        msg.linear_acceleration.x = 9.8  # m/s²
        # ... fill other fields
        
        self.imu_pub.publish(msg)  # Broadcast!
```

### Creating a Subscriber (Code)

```python
from geometry_msgs.msg import Twist

class OrbiBotHardwareNode(Node):
    def __init__(self):
        super().__init__('orbibot_hardware_node')
        
        # Create subscriber
        self.cmd_vel_sub = self.create_subscription(
            Twist,              # Message type
            '/cmd_vel',         # Topic name
            self.cmd_vel_callback,  # Function to call
            10                  # Queue size
        )
    
    def cmd_vel_callback(self, msg: Twist):
        # This runs every time /cmd_vel receives a message!
        vx = msg.linear.x   # Extract forward velocity
        vy = msg.linear.y   # Extract sideways velocity
        vz = msg.angular.z  # Extract rotation rate
        
        # Send to hardware...
        self.get_logger().info(f"Command: vx={vx}, vy={vy}")
```

### Visualizing Topics

```bash
# List all topics
ros2 topic list

# See message type
ros2 topic info /cmd_vel

# Watch data flowing
ros2 topic echo /cmd_vel

# Check publish rate
ros2 topic hz /odom
```

---

## 🔧 Services: Request-Response

### What is a Service?

A **Service** is like calling a function over the network:
- Send a **Request**
- Get a **Response**

### Analogy: Restaurant Order

```
Customer (Client)                    Restaurant (Server)
     │                                        │
     │ "I'd like a pizza" (Request)          │
     │───────────────────────────────────────→│
     │                                        │ Makes pizza
     │ "Here's your pizza" (Response)        │
     │←───────────────────────────────────────│
     │                                        │

One-to-one communication with guaranteed response!
```

### When to Use Services vs Topics

| Use Services When... | Use Topics When... |
|---------------------|-------------------|
| One-time action needed | Continuous data stream |
| Need confirmation | Fire-and-forget |
| Infrequent operations | High-frequency updates |
| Examples: enable motors, reset odometry | Examples: sensor data, velocity commands |

### Services in OrbiBot Hardware

#### 1. /orbibot/set_motor_enable

```python
# Service Type: orbibot_msgs/srv/SetMotorEnable

# Request:
enable: true   # or false

# Response:
success: true
message: "Motors enabled"
```

**Usage:**
```bash
# Enable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Response:
# success: true
# message: "Motors enabled"
```

**Why a service?** 
- One-time action
- Need to know if it succeeded
- Not continuous data

#### 2. /orbibot/reset_odometry

```python
# Service Type: orbibot_msgs/srv/ResetOdometry

# Request:
reset_pose: ...  # (currently ignored by firmware)

# Response:
success: true
message: "Odometry reset to zero"
```

**Usage:**
```bash
ros2 service call /orbibot/reset_odometry orbibot_msgs/srv/ResetOdometry "{}"
```

### Creating a Service (Code)

```python
from orbibot_msgs.srv import SetMotorEnable

class OrbiBotHardwareNode(Node):
    def __init__(self):
        super().__init__('orbibot_hardware_node')
        
        # Create service
        self.motor_srv = self.create_service(
            SetMotorEnable,              # Service type
            '/orbibot/set_motor_enable', # Service name
            self.motor_enable_callback   # Handler function
        )
    
    def motor_enable_callback(self, request, response):
        # request.enable = true or false
        
        if request.enable:
            self.motors_enabled = True
            response.success = True
            response.message = "Motors enabled"
        else:
            self.motors_enabled = False
            response.success = True
            response.message = "Motors disabled"
        
        return response  # Must return the response object!
```

---

## ⏰ Timers: Periodic Tasks

### What is a Timer?

A **Timer** calls a function repeatedly at a fixed interval.

### Analogy: Alarm Clock

```
Alarm Clock Setting:
  "Beep every 10 seconds"

Timer in ROS 2:
  "Call this function every 0.02 seconds (50Hz)"
```

### Why Timers Matter for Hardware

| Task | Frequency | Why This Rate? |
|------|-----------|----------------|
| IMU publishing | 50Hz (20ms) | Fast enough for control |
| Odometry publishing | 50Hz (20ms) | Navigation needs updates |
| Status monitoring | 10Hz (100ms) | Battery changes slowly |
| Safety checks | 10Hz (100ms) | Emergency detection |

### Creating a Timer (Code)

```python
class OrbiBotHardwareNode(Node):
    def __init__(self):
        super().__init__('orbibot_hardware_node')
        
        # Create 50Hz timer (period = 1/50 = 0.02 seconds)
        self.sensor_timer = self.create_timer(
            0.02,                    # Period in seconds
            self.sensor_callback     # Function to call
        )
        
        # Create 10Hz timer
        self.status_timer = self.create_timer(
            0.1,                     # 100ms
            self.status_callback
        )
    
    def sensor_callback(self):
        # This runs 50 times per second!
        self.publish_imu()
        self.publish_odometry()
        self.publish_encoders()
    
    def status_callback(self):
        # This runs 10 times per second
        self.publish_battery()
        self.check_safety()
```

### Frequency vs Period

| Frequency (Hz) | Period (ms) | Use Case |
|----------------|-------------|----------|
| 1 Hz | 1000 ms | Slow monitoring |
| 10 Hz | 100 ms | Status updates |
| 50 Hz | 20 ms | Sensor data |
| 100 Hz | 10 ms | Fast control |

**Conversion:**
```
Period = 1 / Frequency
Frequency = 1 / Period

Example:
  50 Hz → 1/50 = 0.02 s = 20 ms
```

---

## 📦 Message Types Deep Dive

### geometry_msgs/Twist

**Purpose:** Velocity commands

```python
# 3D velocity in free space
Twist:
  # Linear velocity (m/s)
  linear:
    x: float  # Forward (+) / Backward (-)
    y: float  # Left (+) / Right (-) - for mecanum!
    z: float  # Up (+) / Down (-) - usually 0
    
  # Angular velocity (rad/s)
  angular:
    x: float  # Roll - rotation around X
    y: float  # Pitch - rotation around Y
    z: float  # Yaw - rotation around Z (turning)
```

**For OrbiBot (2D ground robot):**
- Only use: `linear.x`, `linear.y`, `angular.z`
- Others are always 0

### nav_msgs/Odometry

**Purpose:** Position and velocity estimate

```python
Odometry:
  header:          # When and in what frame
    stamp: Time
    frame_id: string  # "odom"
  
  child_frame_id: string  # "base_link"
  
  pose:            # Position and orientation
    pose:
      position: Point(x, y, z)
      orientation: Quaternion(x, y, z, w)
    covariance: float[36]  # Uncertainty matrix
  
  twist:           # Velocity
    twist:
      linear: Vector3(x, y, z)
      angular: Vector3(x, y, z)
    covariance: float[36]
```

### sensor_msgs/Imu

**Purpose:** IMU sensor data

```python
Imu:
  header:
    stamp: Time
    frame_id: string  # "imu_link"
  
  orientation: Quaternion  # From sensor fusion
  
  orientation_covariance: float[9]
  
  angular_velocity: Vector3  # Gyroscope (rad/s)
    x: roll rate
    y: pitch rate
    z: yaw rate
  
  angular_velocity_covariance: float[9]
  
  linear_acceleration: Vector3  # Accelerometer (m/s²)
    x: forward/back acceleration
    y: left/right acceleration
    z: up/down (gravity ≈ 9.8 m/s²)
  
  linear_acceleration_covariance: float[9]
```

### std_msgs/Float32MultiArray

**Purpose:** PID parameters

```python
Float32MultiArray:
  layout: ...  # Array structure info
  data: float[]  # The actual numbers

# For PID: [kp, ki, kd]
# Example: data: [0.8, 0.06, 0.5]
```

---

## 🔍 Complete Data Flow Example

### Scenario: Robot Moving in Square Pattern

```
TIME 0s: Initial State
┌─────────────────────────────────────────────────────────────┐
│ Robot at (0, 0), facing East (0°)                           │
│ All topics idle                                             │
└─────────────────────────────────────────────────────────────┘

TIME 0.1s: Command Received
┌─────────────────────────────────────────────────────────────┐
│ teleop_node PUBLISHES to /cmd_vel                           │
│   Twist(linear.x=0.5, angular.z=0.0)                        │
│                                                             │
│ hardware_node SUBSCRIBES, receives message                  │
│   cmd_vel_callback() runs                                   │
│   Sends to firmware: "Move 0.5 m/s forward"                 │
└─────────────────────────────────────────────────────────────┘

TIME 0.1-2.0s: Robot Moves
┌─────────────────────────────────────────────────────────────┐
│ Robot moves forward 1 meter                                 │
│ Encoders measure wheel rotation                             │
│                                                             │
│ Every 20ms (50Hz):                                          │
│   hardware_node PUBLISHES to /odom                          │
│     Position updates: (0.1, 0), (0.2, 0), (0.3, 0)...       │
│                                                             │
│   control_manager SUBSCRIBES, updates navigation            │
└─────────────────────────────────────────────────────────────┘

TIME 2.0s: Turn Command
┌─────────────────────────────────────────────────────────────┐
│ teleop_node PUBLISHES to /cmd_vel                           │
│   Twist(linear.x=0.0, angular.z=0.785)  # 45°/s             │
│                                                             │
│ Robot turns 90° left                                        │
│ Orientation updates in /odom                                │
└─────────────────────────────────────────────────────────────┘

TIME 2.0-10.0s: Complete Square
┌─────────────────────────────────────────────────────────────┐
│ Pattern: Forward → Turn → Forward → Turn → ...              │
│                                                             │
│ Continuous:                                                 │
│   /cmd_vel: Commands sent by teleop                         │
│   /odom: Position published by hardware_node                │
│   /imu/data: Orientation published 50Hz                     │
│                                                             │
│ Services used:                                              │
│   /orbibot/set_motor_enable: Enable at start                │
│   /orbibot/reset_odometry: Reset position if needed         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Hands-On Practice

### Exercise 1: Explore Topics

```bash
# 1. List all topics
ros2 topic list

# 2. Check hardware node topics specifically
ros2 topic list | grep -E "(orbibot|cmd_vel|odom|imu)"

# 3. Get topic info
ros2 topic info /cmd_vel
ros2 topic info /odom

# 4. Echo a topic (watch data flow)
ros2 topic echo /odom --once  # Single message
```

### Exercise 2: Publish Test Commands

```bash
# Terminal 1: Watch commands
ros2 topic echo /cmd_vel

# Terminal 2: Send test command
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}}"

# Terminal 2: Different commands
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {y: 0.2}}"  # Sideways (mecanum!)

ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{angular: {z: 0.5}}"  # Rotate
```

### Exercise 3: Call Services

```bash
# List services
ros2 service list | grep orbibot

# Call motor enable service
ros2 service call /orbibot/set_motor_enable \
  orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Check service type details
ros2 interface show orbibot_msgs/srv/SetMotorEnable
```

---

## 📚 Key Takeaways

1. **Nodes** are single-purpose programs
2. **Topics** are broadcast channels (many-to-many)
3. **Services** are request-response (one-to-one)
4. **Timers** enable periodic tasks
5. **Messages** have specific types with defined structure

### Common Patterns in `orbibot_hardware`

```
┌────────────────────────────────────────────────────────────┐
│                    HARDWARE NODE PATTERN                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  SUBSCRIBE to /cmd_vel ───────────────────────────────┐   │
│       │                                                │   │
│       ▼                                                │   │
│  CALLBACK: Convert to serial protocol                  │   │
│       │                                                │   │
│       ▼                                                │   │
│  SEND to firmware ────────────────────────────────────│───┤
│       │                                                │   │
│       ▼                                                │   │
│  TIMER @ 50Hz: Read sensors from firmware ────────────┤   │
│       │                                                │   │
│       ▼                                                │   │
│  PUBLISH to /odom, /imu/data, etc. ◄──────────────────┘   │
│                                                            │
│  SERVICES:                                                 │
│    /orbibot/set_motor_enable ──► Enable/disable motors    │
│    /orbibot/reset_odometry ────► Reset position to zero   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🚀 Next Steps

Now you understand ROS 2 basics. Next, see how the hardware components fit together:

**→ Continue to:** [[02-hardware-architecture]]

---

## 💭 Review Questions

1. **What's the difference between a Topic and a Service?**
   <details>
   <summary>Click for answer</summary>
   Topics are continuous broadcast (many subscribers, no response). Services are one-time request-response (guaranteed answer).
   </details>

2. **Why does hardware_node use a Timer for sensors?**
   <details>
   <summary>Click for answer</summary>
   Sensors need to be read and published at a consistent rate (50Hz). Timers ensure this happens automatically.
   </details>

3. **What message type does /cmd_vel use? What fields matter for OrbiBot?**
   <details>
   <summary>Click for answer</summary>
   geometry_msgs/Twist. For OrbiBot: linear.x (forward/back), linear.y (left/right), angular.z (rotation).
   </details>

---

**Great progress! You now know ROS 2 fundamentals! 🎉**