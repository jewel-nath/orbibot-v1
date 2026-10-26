# 08 - Launch Files

**Starting multiple nodes together**

---

## 🎯 Learning Objectives

- Create Python launch files
- Launch multiple nodes
- Pass parameters and arguments

---

## 🚀 Why Launch Files?

**Problem:** Starting a robot requires many nodes:

```bash
# Manual start - tedious!
ros2 run hardware hardware_node
ros2 run sensors lidar_node
ros2 run navigation nav_node
ros2 run rviz2 rviz2
```

**Solution:** One launch file starts everything:

```bash
ros2 launch my_robot robot.launch.py
```

---

## 📝 Basic Launch File

```python
# launch/my_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Node 1
        Node(
            package='hardware',
            executable='hardware_node',
            name='hardware'
        ),
        
        # Node 2
        Node(
            package='sensors',
            executable='lidar_node',
            name='lidar'
        ),
    ])
```

---

## 📦 OrbiBot Hardware Launch

```python
# launch/hardware.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument

def generate_launch_description():
    # Declare launch arguments
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/motordriver',
        description='Serial port for motor driver'
    )
    
    motors_enabled_arg = DeclareLaunchArgument(
        'motors_enabled',
        default_value='true',
        description='Auto-enable motors'
    )
    
    # Get argument values
    serial_port = LaunchConfiguration('serial_port')
    motors_enabled = LaunchConfiguration('motors_enabled')
    
    return LaunchDescription([
        serial_port_arg,
        motors_enabled_arg,
        
        Node(
            package='orbibot_hardware',
            executable='hardware_node',
            name='orbibot_hardware_node',
            parameters=[{
                'hardware.serial_port': serial_port,
                'control.motors_enabled': motors_enabled
            }],
            respawn=True  # Restart if crashes
        ),
        
        Node(
            package='orbibot_hardware',
            executable='system_monitor',
            name='system_monitor',
            respawn=True
        ),
    ])
```

---

## 🖥️ Using Launch Files

```bash
# Launch with defaults
ros2 launch orbibot_hardware hardware.launch.py

# Override arguments
ros2 launch orbibot_hardware hardware.launch.py \
  serial_port:=/dev/ttyUSB0 \
  motors_enabled:=false

# View launch file
ros2 launch --show-args orbibot_hardware hardware.launch.py
```

---

## 🎯 Key Takeaways

1. **Launch files** start multiple nodes
2. **generate_launch_description()** returns LaunchDescription
3. **Arguments** make launch files flexible
4. **respawn=True** restarts crashed nodes

---

## 📖 Next Steps

Learn CLI tools:

**→ Continue to:** [12 - CLI Tools](12-cli-tools.md)

---

*Last Updated: March 2026*