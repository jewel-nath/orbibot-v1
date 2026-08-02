---
title: "12 - CLI Tools"
type: learn
area: ros2
tags:
  - learn
  - ros2
---

# 12 - CLI Tools

**Command line tools for ROS2 debugging**

---

## 🎯 Learning Objectives

- Master essential ROS2 CLI commands
- Debug nodes, topics, services
- Record and analyze data

---

## 📋 Essential Commands

### ros2 node

```bash
# List all nodes
ros2 node list

# Info about a node
ros2 node info /hardware_node

# List node's subscribers, publishers, services
```

### ros2 topic

```bash
# List topics
ros2 topic list

# List with types
ros2 topic list -t

# Echo (monitor) a topic
ros2 topic echo /odom

# Echo once
ros2 topic echo /odom --once

# Publish from CLI
ros2 topic pub /cmd_vel geometry_msgs/Twist "linear: {x: 0.5}"

# Check frequency
ros2 topic hz /odom

# Check bandwidth
ros2 topic bw /odom
```

### ros2 service

```bash
# List services
ros2 service list

# List with types
ros2 service list -t

# Call a service
ros2 service call /reset std_srvs/Empty {}

# Show service type
ros2 service type /reset
```

### ros2 param

```bash
# List parameters
ros2 param list /hardware_node

# Get value
ros2 param get /hardware_node max_velocity

# Set value
ros2 param set /hardware_node max_velocity 0.5

# Dump to file
ros2 param dump /hardware_node > params.yaml
```

### ros2 bag

```bash
# Record topics
ros2 bag record /odom /imu/data

# Record all
ros2 bag record -a

# Play back
ros2 bag play rosbag2_2024_...

# Info about bag
ros2 bag info rosbag2_2024_...
```

### ros2 run

```bash
# Run a node
ros2 run package_name node_name

# Run with parameters
ros2 run hardware hardware_node --ros-args -p port:="/dev/ttyUSB0"
```

### ros2 launch

```bash
# Launch a file
ros2 launch package_name launch_file.py

# With arguments
ros2 launch hardware hardware.launch.py port:="/dev/ttyUSB0"

# Show launch arguments
ros2 launch --show-args hardware hardware.launch.py
```

---

## 🔍 Debugging Workflow

```
1. What's running?
   ros2 node list

2. What topics?
   ros2 topic list

3. Is data flowing?
   ros2 topic echo /topic_name

4. What's the rate?
   ros2 topic hz /topic_name

5. Check node info
   ros2 node info /node_name

6. Check parameters
   ros2 param list /node_name
```

---

## 🎯 Key Takeaways

| Command | Purpose |
|---------|---------|
| `ros2 node list` | See running nodes |
| `ros2 topic echo` | Monitor data |
| `ros2 topic hz` | Check frequency |
| `ros2 service call` | Test services |
| `ros2 param get/set` | Configure nodes |
| `ros2 bag record/play` | Save/replay data |

---

## 📖 Next Steps

Practice with your robot!

**Or review:** [[03-topics-pub-sub]] for topic details

---

*Last Updated: March 2026*