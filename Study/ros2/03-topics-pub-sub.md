# 03 - Topics and Pub/Sub

**The heart of ROS2 communication**

---

## 🎯 Learning Objectives

- Understand what topics are
- Create publishers and subscribers
- Know QoS (Quality of Service) policies
- Use ROS2 CLI tools for topics

---

## 📡 What is a Topic?

A **topic** is a named bus over which nodes exchange messages.

### Analogy: Radio Station

```
Radio Station (Topic): /weather_report
├── Radio Tower (Publisher): Broadcasts weather
├── Car Radio 1 (Subscriber): Listens while driving
├── Home Radio 2 (Subscriber): Listens at home  
└── Phone App 3 (Subscriber): Listens on mobile

One publisher, many subscribers!
```

### ROS2 Example

```
Topic: /cmd_vel (velocity commands)
├── Publisher: teleop_node (gamepad input)
├── Publisher: navigation_node (autonomous)
└── Subscriber: hardware_node (controls motors)
```

---

## 📝 Creating a Publisher

### Minimal Example

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Talker(Node):
    def __init__(self):
        super().__init__('talker')
        
        # Create publisher
        self.publisher = self.create_publisher(
            String,      # Message type
            'chatter',   # Topic name
            10           # Queue size
        )
        
        # Timer to publish every 0.5 seconds
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.i = 0
    
    def timer_callback(self):
        msg = String()
        msg.data = f'Hello World: {self.i}'
        self.publisher.publish(msg)
        self.get_logger().info(f'Publishing: "{msg.data}"')
        self.i += 1

def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Key Parts Explained

```python
self.create_publisher(String, 'chatter', 10)
#     ↑                    ↑        ↑      ↑
#   Method            Msg type  Topic  Queue size
```

**Queue size:** How many messages to buffer if subscribers are slow.

---

## 📥 Creating a Subscriber

### Minimal Example

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class Listener(Node):
    def __init__(self):
        super().__init__('listener')
        
        # Create subscriber
        self.subscription = self.create_subscription(
            String,           # Message type
            'chatter',        # Topic name
            self.listener_callback,  # Callback function
            10                # Queue size
        )
    
    def listener_callback(self, msg):
        # This runs every time a message arrives!
        self.get_logger().info(f'I heard: "{msg.data}"')

def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Callback Pattern

```python
def listener_callback(self, msg):
    # msg is the received message
    # Process it immediately (keep it fast!)
```

**Important:** Callbacks should be fast. If you need to do slow work, use a queue or separate thread.

---

## 🔧 Common Message Types

| Type | Use For | Fields |
|------|---------|--------|
| `std_msgs/String` | Text | `data` |
| `std_msgs/Float64` | Single number | `data` |
| `geometry_msgs/Twist` | Velocity | `linear`, `angular` |
| `sensor_msgs/LaserScan` | LIDAR data | `ranges`, `angles` |
| `nav_msgs/Odometry` | Position | `pose`, `twist` |

### Example: Twist Message

```python
from geometry_msgs.msg import Twist

msg = Twist()
msg.linear.x = 0.5   # m/s forward
msg.linear.y = 0.0   # m/s sideways
msg.angular.z = 0.1  # rad/s rotation
```

---

## ⚙️ QoS (Quality of Service)

QoS controls how messages are delivered.

### Common QoS Profiles

| Profile | Use Case | Behavior |
|---------|----------|----------|
| **Reliable** | Important data | Guaranteed delivery, may delay |
| **Best Effort** | Sensor streams | Fast, some loss OK |
| **Transient Local** | Config data | New subscribers get last value |

### Setting QoS

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy

# Reliable - for important commands
reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    depth=10
)

# Best Effort - for high-frequency sensor data
best_effort_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    depth=5
)

self.pub = self.create_publisher(Twist, '/cmd_vel', reliable_qos)
```

### OrbiBot Examples

| Topic | QoS | Why |
|-------|-----|-----|
| `/cmd_vel` | Reliable | Commands must arrive |
| `/odom` | Reliable | Position data critical |
| `/imu/data` | Best Effort | 50Hz stream, next message soon |
| `/scan` | Best Effort | LIDAR data, high frequency |

---

## 🖥️ CLI Tools for Topics

### List Topics

```bash
# All topics
ros2 topic list

# With types
ros2 topic list -t

# Filter
ros2 topic list | grep orbibot
```

### Echo (Monitor)

```bash
# Watch data in real-time
ros2 topic echo /chatter

# Just one message
ros2 topic echo /chatter --once

# Specific field
ros2 topic echo /odom/pose/pose/position
```

### Topic Info

```bash
# Publishers and subscribers
ros2 topic info /chatter

# Message type
ros2 topic type /chatter

# Show message definition
ros2 interface show std_msgs/String
```

### Publish from Command Line

```bash
# One-time publish
ros2 topic pub --once /chatter std_msgs/String "data: 'Hello'"

# Continuous publish at 1Hz
ros2 topic pub /chatter std_msgs/String "data: 'Hello'" --rate 1

# Publish Twist
ros2 topic pub --once /cmd_vel geometry_msgs/Twist \
  "linear: {x: 0.5}, angular: {z: 0.1}"
```

### Bandwidth and Rate

```bash
# Check publish rate
ros2 topic hz /chatter

# Check bandwidth usage
ros2 topic bw /chatter
```

---

## 🔄 Complete Example: OrbiBot Hardware

### Publisher (hardware_node)

```python
from sensor_msgs.msg import Imu

class HardwareNode(Node):
    def __init__(self):
        super().__init__('hardware_node')
        
        # Publish IMU data at 50Hz
        self.imu_pub = self.create_publisher(
            Imu, '/imu/data', 10
        )
        self.timer = self.create_timer(0.02, self.publish_imu)
    
    def publish_imu(self):
        msg = Imu()
        # Fill with sensor data...
        msg.linear_acceleration.x = 0.0
        msg.linear_acceleration.y = 0.0
        msg.linear_acceleration.z = 9.8
        
        self.imu_pub.publish(msg)
```

### Subscriber (control_node)

```python
from sensor_msgs.msg import Imu

class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')
        
        # Subscribe to IMU
        self.imu_sub = self.create_subscription(
            Imu, '/imu/data', self.imu_callback, 10
        )
    
    def imu_callback(self, msg):
        # Process IMU data
        accel_z = msg.linear_acceleration.z
        self.get_logger().info(f'Gravity: {accel_z} m/s²')
```

---

## 🎯 Best Practices

### DO:

```
✅ Keep callback functions fast (<10ms)
✅ Use appropriate QoS for your data
✅ Choose descriptive topic names
✅ Check topic rates match your needs
✅ Use --once flag for testing
```

### DON'T:

```
❌ Do heavy computation in callbacks
❌ Use Reliable QoS for high-frequency data
❌ Create too many topics (hard to debug)
❌ Forget to handle missing data
```

---

## 🧪 Exercise

### Create a Simple Pub/Sub System

1. **Create publisher node:**
```python
# Publishes countdown from 10 to 0
```

2. **Create subscriber node:**
```python
# Prints "Liftoff!" when it receives 0
```

3. **Test with CLI:**
```bash
ros2 topic pub /count std_msgs/Int32 "data: 5"
ros2 topic echo /count
```

---

## 🎯 Key Takeaways

1. **Topics** are named data streams (many-to-many)
2. **Publishers** send data
3. **Subscribers** receive data via callbacks
4. **QoS** controls delivery reliability
5. **CLI tools** help debug and test

---

## 📖 Next Steps

Learn about message interfaces:

**→ Continue to:** [04-messages-interfaces.md](04-messages-interfaces.md)

---

*Last Updated: March 2026*