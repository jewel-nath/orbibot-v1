# 11 - Practical Exercises

**Hands-on exercises to master orbibot_hardware**

---

## 🎯 Overview

Complete these exercises to solidify your understanding. Each exercise builds on previous knowledge.

**Prerequisites:**
- ROS 2 installed
- OrbiBot workspace built
- Hardware connected (or use simulation mode)

---

## 📋 Exercise Checklist

| Exercise | Topic | Difficulty | Time |
|----------|-------|------------|------|
| 1 | Topic exploration | Easy | 15 min |
| 2 | Manual motor control | Easy | 20 min |
| 3 | Sensor data analysis | Medium | 30 min |
| 4 | Parameter tuning | Medium | 25 min |
| 5 | Code modification | Hard | 45 min |
| 6 | Safety system testing | Medium | 20 min |
| 7 | Custom publisher | Hard | 40 min |

---

## 📝 Exercise 1: Topic Exploration

**Goal:** Understand all topics published by hardware_node

### Steps

```bash
# 1. Launch hardware node
ros2 launch orbibot_hardware hardware.launch.py

# 2. In a new terminal, list all topics
ros2 topic list

# 3. For each orbibot topic, get info
ros2 topic info /orbibot/system_status
ros2 topic info /orbibot/safety_status
ros2 topic info /orbibot/encoders

# 4. Echo each topic (press Ctrl+C after seeing a few messages)
ros2 topic echo /imu/data --once
ros2 topic echo /odom --once
ros2 topic echo /joint_states --once

# 5. Check message rates
ros2 topic hz /imu/data
ros2 topic hz /odom
ros2 topic hz /orbibot/system_status
```

### Questions

1. Which topics publish at 50Hz? Which at 10Hz?
2. What message type does `/odom` use?
3. What information is in `/orbibot/system_status`?

### Expected Answers

<details>
<summary>Click for answers</summary>

1. **50Hz:** /imu/data, /imu/data_raw, /odom, /joint_states, /orbibot/encoders
   **10Hz:** /orbibot/system_status, /orbibot/safety_status, /diagnostics

2. **nav_msgs/Odometry**

3. **Battery voltage, motors enabled status, emergency stop status, hardware OK status**
</details>

---

## 📝 Exercise 2: Manual Motor Control

**Goal:** Control robot using command line

### Steps

```bash
# Terminal 1: Launch hardware
ros2 launch orbibot_hardware hardware.launch.py

# Terminal 2: Enable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Terminal 3: Send movement commands
# Forward
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"

# Backward
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.2}}"

# Left (mecanum!)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {y: 0.2}}"

# Right
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {y: -0.2}}"

# Rotate clockwise
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}"

# Rotate counter-clockwise
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{angular: {z: -0.5}}"

# Stop
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{}"
```

### Challenge

Try to make the robot move in a square pattern:
1. Forward 1 second
2. Turn 90°
3. Repeat 4 times

```bash
# Hint: Use this pattern
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
sleep 1
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 1.57}}"
sleep 1
# ... repeat
```

---

## 📝 Exercise 3: Sensor Data Analysis

**Goal:** Understand IMU and odometry data

### Steps

```bash
# 1. Launch hardware
ros2 launch orbibot_hardware hardware.launch.py

# 2. Terminal 1: Monitor IMU
ros2 topic echo /imu/data/linear_acceleration/z

# 3. Terminal 2: Monitor orientation
ros2 topic echo /imu/data/orientation

# 4. Terminal 3: Monitor odometry
ros2 topic echo /odom/pose/pose/position/x /odom/pose/pose/position/y

# 5. Manually move robot (or send commands) and observe changes
```

### Analysis Questions

1. **IMU Z acceleration** - What value do you see when robot is stationary?
   <details>
   <summary>Answer</summary>
   ~9.8 m/s² (gravity!)
   </details>

2. **Orientation** - What are the quaternion values when facing:
   - Forward (0°)?
   - Left (90°)?
   - Backward (180°)?

3. **Odometry** - Reset odometry and drive forward 1m. What X value?

### Experiment: IMU Response

```bash
# Watch linear acceleration while robot moves
ros2 topic echo /imu/data/linear_acceleration

# Move robot forward and backward
# Q: What happens to X acceleration?
# Q: What happens to Z acceleration?
```

---

## 📝 Exercise 4: Parameter Tuning

**Goal:** Modify behavior via parameters

### Steps

```bash
# 1. View current parameters
ros2 param list /orbibot_hardware_node

# 2. Get specific parameter
ros2 param get /orbibot_hardware_node control.max_velocity

# 3. Launch with custom parameter
ros2 launch orbibot_hardware hardware.launch.py max_velocity:=0.3

# 4. Test - try sending high velocity command
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}}"
# Robot should only move at 0.3 m/s (clamped)
```

### Experiments

1. **Change timeout** - Set cmd_timeout to 0.5s
   - Send command
   - Wait - does robot stop faster?

2. **Change velocity limit** - Set max_velocity to 0.1 m/s
   - Robot should move very slowly

3. **Modify YAML** - Edit `config/hardware_params.yaml`:
   ```yaml
   control:
     max_velocity: 0.5
     cmd_timeout: 1.0
   ```
   - Rebuild and test

---

## 📝 Exercise 5: Code Modification

**Goal:** Add custom logging to hardware_node

### Task

Add a log message whenever velocity is clamped.

### Steps

1. **Open file:**
   ```bash
   code ~/orbibot_ws/src/orbibot_hardware/orbibot_hardware/hardware_node.py
   ```

2. **Find the clamping code** (in `_cmd_vel_callback`):
   ```python
   vx = max(-self.max_velocity, min(msg.linear.x, self.max_velocity))
   ```

3. **Add logging:**
   ```python
   # Before clamping
   original_vx = msg.linear.x
   
   # Clamp
   vx = max(-self.max_velocity, min(msg.linear.x, self.max_velocity))
   
   # Log if clamped
   if vx != original_vx:
       self.get_logger().warn(f"Velocity clamped: {original_vx} -> {vx}")
   ```

4. **Rebuild:**
   ```bash
   cd ~/orbibot_ws
   colcon build --packages-select orbibot_hardware
   source install/setup.bash
   ```

5. **Test:**
   ```bash
   ros2 launch orbibot_hardware hardware.launch.py max_velocity:=0.3
   ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}}"
   # Should see warning log
   ```

---

## 📝 Exercise 6: Safety System Testing

**Goal:** Verify safety features work

### Test 1: Command Timeout

```bash
# Terminal 1: Launch with short timeout
ros2 launch orbibot_hardware hardware.launch.py cmd_timeout:=1.0

# Terminal 2: Enable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Terminal 3: Start movement
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
# Keep publishing every 0.5s

# Stop publishing - wait 2 seconds
# Robot should stop automatically
```

### Test 2: Battery Protection

```bash
# Monitor battery
ros2 topic echo /orbibot/system_status/battery_voltage

# If you have adjustable power supply:
# Slowly decrease voltage below 11.0V
# Watch for warnings

# Below 10.5V: Motors should disable automatically
```

### Test 3: Motor Enable Safety

```bash
# Without enabling motors, try to move
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
# Robot should NOT move

# Now enable and try again
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
# Robot should move
```

---

## 📝 Exercise 7: Custom Publisher (Challenge)

**Goal:** Create a node that publishes custom commands

### Task

Create a Python node that:
1. Publishes velocity commands in a circle pattern
2. Logs current odometry position
3. Stops after completing one circle

### Template

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math

class CircleDriver(Node):
    def __init__(self):
        super().__init__('circle_driver')
        
        # Publisher
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Subscriber
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        
        # Timer (10Hz)
        self.timer = self.create_timer(0.1, self.timer_callback)
        
        # State
        self.start_x = None
        self.start_y = None
        self.angle = 0.0
        
        self.get_logger().info("Circle driver started")
    
    def odom_callback(self, msg):
        # Store position
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        
        # Record start position
        if self.start_x is None:
            self.start_x = self.current_x
            self.start_y = self.current_y
    
    def timer_callback(self):
        if self.start_x is None:
            return  # Wait for first odometry
        
        # TODO: Calculate distance from start
        # TODO: Calculate velocity for circular motion
        # TODO: Publish Twist message
        # TODO: Stop after completing circle
        
        pass  # Replace with your code

def main(args=None):
    rclpy.init(args=args)
    node = CircleDriver()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Hints

```python
# Circular motion parameters
radius = 1.0  # meters
speed = 0.2   # m/s

# Calculate angular velocity
angular_z = speed / radius

# Publish
msg = Twist()
msg.linear.x = speed
msg.angular.z = angular_z
self.cmd_pub.publish(msg)

# Check if completed circle
distance = math.sqrt(
    (self.current_x - self.start_x)**2 + 
    (self.current_y - self.start_y)**2
)
# If distance < 0.1 and angle > 2*pi, stop
```

### Run Your Solution

```bash
# Terminal 1: Launch hardware
ros2 launch orbibot_hardware hardware.launch.py

# Terminal 2: Enable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Terminal 3: Run your node
ros2 run your_package circle_driver

# Terminal 4: Watch in RViz
ros2 run rviz2 rviz2
# Add Odometry display, set topic to /odom
```

---

## 🎓 Final Challenge: Complete Integration

### Goal

Create a complete test routine that:
1. Enables motors
2. Drives in square pattern
3. Logs battery voltage at each corner
4. Returns to start position
5. Disables motors

### Bonus Points

- Use odometry to detect when to turn (not just time)
- Verify position accuracy
- Create a ROS service to start/stop the routine

---

## ✅ Completion Checklist

After completing these exercises, you should be able to:

- [ ] List and describe all hardware topics
- [ ] Manually control robot via command line
- [ ] Interpret IMU and odometry data
- [ ] Modify parameters and observe effects
- [ ] Make simple code modifications
- [ ] Verify safety systems work
- [ ] Create custom ROS nodes

---

## 📚 Congratulations!

You have completed the OrbiBot Hardware study guide!

**Next steps:**
- Explore other packages (control_manager, navigation)
- Read firmware architecture documentation
- Contribute improvements to the codebase
- Build your own robot projects!

---

**Happy robot building! 🤖🎉**