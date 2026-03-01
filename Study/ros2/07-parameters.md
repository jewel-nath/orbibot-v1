# 07 - Parameters

**Configuration system for ROS2 nodes**

---

## 🎯 Learning Objectives

- Understand what parameters are
- Declare and use parameters
- Set parameters via YAML and CLI

---

## ⚙️ What are Parameters?

**Parameters** are configuration values for nodes.

### Analogy: Car Settings

```
Car (Node) Settings:
├── Max Speed: 120 km/h     ← Parameter
├── Color: Red              ← Parameter
├── Autopilot: Enabled      ← Parameter

Change without rebuilding the car!
```

### ROS2 Parameters

```python
# hardware_node parameters
serial_port: "/dev/motordriver"
max_velocity: 1.0
cmd_timeout: 2.0
```

---

## 📝 Declaring Parameters

```python
import rclpy
from rclpy.node import Node

class ParamNode(Node):
    def __init__(self):
        super().__init__('param_node')
        
        # Declare parameter with default
        self.declare_parameter('max_speed', 1.0)
        self.declare_parameter('timeout', 2.0)
        self.declare_parameter('port', '/dev/ttyUSB0')
        
        # Get parameter values
        max_speed = self.get_parameter('max_speed').value
        timeout = self.get_parameter('timeout').value
        
        self.get_logger().info(f'Max speed: {max_speed}, Timeout: {timeout}')

def main(args=None):
    rclpy.init(args=args)
    node = ParamNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 🔧 Setting Parameters

### Method 1: Command Line

```bash
# Run node with parameters
ros2 run my_package param_node --ros-args -p max_speed:=0.5 -p timeout:=1.0

# Multiple parameters
ros2 run my_package param_node \
  --ros-args \
  -p max_speed:=0.5 \
  -p timeout:=1.0 \
  -p port:="/dev/ttyACM0"
```

### Method 2: YAML File

```yaml
# config/params.yaml
param_node:
  ros__parameters:
    max_speed: 0.5
    timeout: 1.0
    port: "/dev/ttyACM0"
```

```python
# Load in launch file
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='my_package',
            executable='param_node',
            parameters=['config/params.yaml']
        )
    ])
```

### Method 3: Launch File Direct

```python
Node(
    package='my_package',
    executable='param_node',
    parameters=[{
        'max_speed': 0.5,
        'timeout': 1.0
    }]
)
```

---

## 🖥️ CLI Tools for Parameters

```bash
# List parameters of a node
ros2 param list /param_node

# Get parameter value
ros2 param get /param_node max_speed
# Double value is: 0.5

# Set parameter (while running!)
ros2 param set /param_node max_speed 1.0

# Dump all parameters to YAML
ros2 param dump /param_node > params.yaml

# Load from YAML
ros2 param load /param_node params.yaml
```

---

## 🎯 OrbiBot Example

```python
# hardware_node.py
def __init__(self):
    super().__init__('hardware_node')
    
    # Declare all parameters
    self.declare_parameter('hardware.serial_port', '/dev/motordriver')
    self.declare_parameter('control.max_velocity', 1.0)
    self.declare_parameter('control.cmd_timeout', 2.0)
    self.declare_parameter('safety.battery_low_threshold', 11.0)
    
    # Get values
    self.serial_port = self.get_parameter('hardware.serial_port').value
    self.max_velocity = self.get_parameter('control.max_velocity').value
```

---

## 🎯 Key Takeaways

1. **Parameters** = Configuration values
2. **declare_parameter()** = Define with default
3. **get_parameter().value** = Read value
4. **Can change at runtime** via CLI
5. **YAML files** = Persistent configuration

---

## 📖 Next Steps

Learn about launch files:

**→ Continue to:** [08-launch-files.md](08-launch-files.md)

---

*Last Updated: March 2026*