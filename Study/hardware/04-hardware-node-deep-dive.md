# 04 - Hardware Node Deep Dive

**Line-by-line analysis of hardware_node.py**

---

## 🎯 Learning Objectives

After reading this, you will understand:
- How hardware_node.py is structured
- The initialization sequence
- How velocity commands are processed
- How sensor data is published
- Thread safety mechanisms

---

## 📁 File Overview

### Location and Purpose

```python
# File: src/orbibot_hardware/orbibot_hardware/hardware_node.py
# Lines: ~524
# Purpose: Main ROS 2 node for hardware interface
```

### What It Does

```
┌─────────────────────────────────────────────────────────────┐
│ hardware_node.py                                             │
├─────────────────────────────────────────────────────────────┤
│ 1. Initializes ROS 2 node                                    │
│ 2. Connects to STM32 firmware via serial                     │
│ 3. Subscribes to /cmd_vel (velocity commands)                │
│ 4. Publishes sensor data (IMU, odometry, battery)           │
│ 5. Provides services (motor enable, reset odometry)          │
│ 6. Monitors safety (timeout, battery, emergency stop)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Class Structure

### Class Definition

```python
class OrbiBotHardwareNode(Node):
    """
    Hardware interface node for OrbiBot.
    
    Publishes firmware odometry on /odom with adaptive covariance.
    Firmware handles PID + odometry at 100Hz, this node bridges to ROS 2.
    """
```

**Inheritance:** Extends `Node` (ROS 2 base class)

### Key Class Attributes

```python
# Hardware connection
self.bot = None              # Rosmaster driver instance
self.hardware_connected = False

# State variables (thread-safe access)
self.motors_enabled = False
self.emergency_stop = False

# Timing
self._last_cmd_time = time.time()  # For timeout detection

# Wheel tracking for RViz
self.wheel_positions = [0.0, 0.0, 0.0, 0.0]  # FL, BL, FR, BR

# Odometry covariance tracking
self._accumulated_distance = 0.0
self._accumulated_rotation = 0.0
```

---

## 🔧 __init__ Method Walkthrough

### Step 1: Initialize Node

```python
def __init__(self):
    super().__init__('orbibot_hardware_node')  # Node name
```

**What happens:**
- Registers node with ROS 2
- Name appears in `ros2 node list`
- Logger becomes available

### Step 2: Load Parameters

```python
self._declare_parameters()
```

**Loads from:** `config/hardware_params.yaml`

```yaml
hardware:
  serial_port: "/dev/motordriver"

control:
  cmd_timeout: 2.0           # Stop if no command for 2s
  max_velocity: 1.0          # m/s limit
  max_angular_velocity: 2.0  # rad/s limit

safety:
  battery_low_threshold: 11.0     # Volts
  battery_critical_voltage: 10.5  # Emergency stop
```

**Why parameters?**
- Change behavior without recompiling
- Different configs for different robots
- Easy tuning

### Step 3: Initialize State

```python
# State with thread-safe access
self._state_lock = threading.Lock()
self.motors_enabled = False
self.emergency_stop = False

# Command timing
self._cmd_time_lock = threading.Lock()
self._last_cmd_time = time.time()
self._timeout_stop_sent = False
```

**Why locks?**
- Multiple threads access these variables
- Prevents race conditions
- Ensures consistent state

### Step 4: Create ROS Interfaces

```python
self._create_publishers()    # /odom, /imu/data, etc.
self._create_subscribers()   # /cmd_vel, PID topics
self._create_services()      # motor enable, reset odometry
self._create_timers()        # 50Hz sensor, 10Hz status
```

### Step 5: Connect Hardware

```python
self._initialize_hardware()
```

**What it does:**
- Opens serial port
- Creates receive thread
- Enables auto-report
- Sets initial state (stopped)

---

## 📤 Creating Publishers

### The Publisher List

```python
def _create_publishers(self):
    # Sensor data - BEST_EFFORT for speed
    sensor_qos = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        depth=5
    )
    
    self.imu_pub = self.create_publisher(Imu, '/imu/data', sensor_qos)
    self.imu_raw_pub = self.create_publisher(Imu, '/imu/data_raw', sensor_qos)
    self.mag_pub = self.create_publisher(MagneticField, '/imu/mag', sensor_qos)
    self.encoder_pub = self.create_publisher(Int32MultiArray, '/orbibot/encoders', sensor_qos)
    
    # Important data - RELIABLE
    self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
    self.joint_states_pub = self.create_publisher(JointState, '/joint_states', 10)
    
    # Status
    self.system_status_pub = self.create_publisher(SystemStatus, '/orbibot/system_status', 10)
    self.safety_status_pub = self.create_publisher(SafetyStatus, '/orbibot/safety_status', 10)
```

### QoS Explained

| Policy | Use For | Why |
|--------|---------|-----|
| **BEST_EFFORT** | Sensor data | Fast, some loss OK |
| **RELIABLE** | Odometry, status | Must not lose data |

**BEST_EFFORT:** "Send it fast, I don't need confirmation"
**RELIABLE:** "Make sure it arrives, I'll wait for ACK"

---

## 📥 Creating Subscribers

### cmd_vel Subscriber

```python
def _create_subscribers(self):
    control_qos = QoSProfile(
        reliability=ReliabilityPolicy.RELIABLE,
        depth=10
    )
    
    self.cmd_vel_sub = self.create_subscription(
        Twist,              # Message type
        '/cmd_vel',         # Topic name
        self._cmd_vel_callback,  # Handler
        control_qos
    )
```

### PID Parameter Subscribers

```python
# Single-level PID: [kp, ki, kd]
self.pid_sub = self.create_subscription(
    Float32MultiArray, '/orbibot/pid_params',
    self._pid_callback, 10)

# Yaw PID: [kp, ki, kd]
self.yaw_pid_sub = self.create_subscription(
    Float32MultiArray, '/orbibot/yaw_pid_params',
    self._yaw_pid_callback, 10)

# Multi-level PID: [t0,t1,t2, kp0,ki0,kd0, ...]
self.pid_multilevel_sub = self.create_subscription(
    Float32MultiArray, '/orbibot/pid_multilevel',
    self._pid_multilevel_callback, 10)
```

---

## 🔧 cmd_vel Callback Deep Dive

### The Complete Handler

```python
def _cmd_vel_callback(self, msg: Twist):
    """Send velocity commands to firmware"""
    
    # 1. Check hardware connected
    if not self.hardware_connected:
        return
    
    # 2. Update command time (prevents timeout)
    with self._cmd_time_lock:
        self._last_cmd_time = time.time()
        self._timeout_stop_sent = False
    
    # 3. Check motors enabled
    with self._state_lock:
        enabled = self.motors_enabled
    if not enabled:
        return
    
    # 4. Clamp to safe limits
    vx = max(-self.max_velocity, min(msg.linear.x, self.max_velocity))
    vy = max(-self.max_velocity, min(msg.linear.y, self.max_velocity))
    vz = max(-self.max_angular_velocity, min(msg.angular.z, self.max_angular_velocity))
    
    # 5. Send to hardware
    try:
        self.bot.set_car_motion(vx, vy, vz)
    except Exception as e:
        self.get_logger().error(f"Motion command failed: {e}")
```

### Step-by-Step Explanation

**Step 1: Hardware Check**
```python
if not self.hardware_connected:
    return
```
- If serial not connected, ignore command
- Prevents errors from piling up

**Step 2: Update Timing**
```python
with self._cmd_time_lock:
    self._last_cmd_time = time.time()
    self._timeout_stop_sent = False
```
- Records when command received
- Resets timeout flag
- Lock prevents race condition

**Step 3: Motor Enable Check**
```python
with self._state_lock:
    enabled = self.motors_enabled
if not enabled:
    return
```
- Motors must be explicitly enabled
- Safety feature

**Step 4: Velocity Clamping**
```python
vx = max(-self.max_velocity, min(msg.linear.x, self.max_velocity))
```
- Limits velocity to safe range
- `min` caps upper bound
- `max` caps lower bound
- Protects motors and robot

**Step 5: Send Command**
```python
self.bot.set_car_motion(vx, vy, vz)
```
- Calls driver method
- Converts to protocol and sends
- Handles serial communication

---

## ⏰ Timer Callbacks

### Sensor Timer (50Hz)

```python
def _sensor_callback(self):
    """Publish sensor data @ 50Hz"""
    if not self.hardware_connected:
        return
    
    # 1. Check command timeout
    self._check_timeout()
    
    # 2. Publish all sensors
    self._publish_imu()
    self._publish_imu_raw()
    self._publish_mag()
    self._publish_firmware_odom()
    
    # 3. Publish encoders and joint states
    encoders = self.bot.get_motor_encoder()
    if encoders:
        self._publish_encoders(encoders)
        self._publish_joint_states(encoders)
```

### Status Timer (10Hz)

```python
def _status_callback(self):
    """Publish system status @ 10Hz"""
    if not self.hardware_connected:
        return
    
    # Get battery voltage
    battery = self.bot.get_battery_voltage()
    
    # Build status message
    status_msg = SystemStatus()
    status_msg.battery_voltage = battery
    status_msg.motors_enabled = self.motors_enabled
    status_msg.emergency_stop = self.emergency_stop
    
    # Publish
    self.system_status_pub.publish(status_msg)
```

### Safety Timer (10Hz)

```python
def _safety_callback(self):
    """Monitor safety @ 10Hz"""
    
    # Check command timeout
    with self._cmd_time_lock:
        cmd_age = time.time() - self._last_cmd_time
    cmd_timeout = cmd_age > self.cmd_timeout
    
    # Check battery
    battery = self.bot.get_battery_voltage()
    low_battery = battery < self.battery_low_threshold
    critical_battery = battery < self.battery_critical_voltage
    
    # Publish safety status
    safety_msg = SafetyStatus()
    safety_msg.cmd_timeout = cmd_timeout
    safety_msg.low_battery = low_battery
    
    self.safety_status_pub.publish(safety_msg)
    
    # Emergency actions
    if critical_battery:
        self.emergency_stop = True
        self.motors_enabled = False
        self.bot.set_car_motion(0, 0, 0)
```

---

## 🛡️ Timeout Protection Explained

### Why Timeout Matters

```
Scenario: Controller crashes while robot is moving
Without timeout: Robot keeps moving forever! → Crash!
With timeout: Robot stops after 2 seconds → Safe!
```

### Implementation

```python
def _sensor_callback(self):
    # ... other code ...
    
    # Check timeout
    with self._cmd_time_lock:
        cmd_age = time.time() - self._last_cmd_time
        
        # Determine whether to stop
        send_stop = False
        if cmd_age > self.cmd_timeout and self.motors_enabled:
            if not self._timeout_stop_sent:
                self._timeout_stop_sent = True
                send_stop = True
    
    # Send stop OUTSIDE the lock (prevents blocking)
    if send_stop:
        self.bot.set_car_motion(0, 0, 0)
        self.get_logger().warn("Command timeout - stopping")
```

**Key design:** Check inside lock, send outside lock
- Prevents holding lock during serial write (2ms delay)
- Allows new cmd_vel to arrive during send

---

## 📊 Odometry Publishing

### Firmware Odometry Handling

```python
def _publish_firmware_odom(self):
    """Publish firmware odometry with adaptive covariance"""
    
    # Get data from driver
    odom_data = self.bot.get_firmware_odometry()
    x, y, theta, vx, vy, omega = odom_data
    
    # Skip if unchanged (deduplication)
    if odom_data == self._last_firmware_odom:
        return
    self._last_firmware_odom = odom_data
    
    # Update accumulated distance for covariance
    dx = x - self._last_odom_x
    dy = y - self._last_odom_y
    dtheta = abs(((theta - self._last_odom_theta) + math.pi) % (2 * math.pi) - math.pi)
    
    self._accumulated_distance = self._accumulated_distance * self._cov_decay + math.sqrt(dx*dx + dy*dy)
    self._accumulated_rotation = self._accumulated_rotation * self._cov_decay + dtheta
    
    # Build odometry message
    msg = Odometry()
    msg.header.stamp = self.get_clock().now().to_msg()
    msg.header.frame_id = 'odom'
    msg.child_frame_id = 'base_footprint'
    
    # Position
    msg.pose.pose.position.x = x
    msg.pose.pose.position.y = y
    
    # Orientation (yaw to quaternion)
    half_yaw = theta * 0.5
    msg.pose.pose.orientation.z = math.sin(half_yaw)
    msg.pose.pose.orientation.w = math.cos(half_yaw)
    
    # Velocity
    msg.twist.twist.linear.x = vx
    msg.twist.twist.angular.z = omega
    
    # Adaptive covariance (grows with distance)
    pos_var = self._cov_pose_base + self._accumulated_distance * self._cov_pose_drift
    yaw_var = self._cov_yaw_base + self._accumulated_rotation * self._cov_yaw_drift
    
    # Fill covariance matrix (6x6)
    msg.pose.covariance = [
        pos_var, 0, 0, 0, 0, 0,
        0, pos_var, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, yaw_var
    ]
    
    # Publish
    self.odom_pub.publish(msg)
```

---

## 🧵 Thread Safety Deep Dive

### Why Threads?

```
Main Thread:          Receive Thread:
- Timers               - Continuously read serial
- Callbacks            - Parse incoming packets
- Publishing           - Update internal state
```

### Locks Used

| Lock | Protects | Why |
|------|----------|-----|
| `_state_lock` | motors_enabled, emergency_stop | Service callbacks + timers |
| `_cmd_time_lock` | _last_cmd_time, _timeout_stop_sent | cmd_vel callback + timer |
| `_write_lock` (in driver) | Serial writes | Prevent packet interleaving |
| `_data_lock` (in driver) | Sensor variables | Parse vs read race |

### Example: Safe State Access

```python
# WRONG - Race condition!
def enable_motors(self):
    self.motors_enabled = True  # Timer might read mid-write!

# CORRECT - Locked access
def enable_motors(self):
    with self._state_lock:
        self.motors_enabled = True
```

---

## 🔌 Service Callbacks

### Motor Enable Service

```python
def _motor_enable_callback(self, request, response):
    """Enable/disable motors"""
    try:
        with self._state_lock:
            if request.enable and not self.emergency_stop:
                # Enable motors
                self.motors_enabled = True
                response.success = True
                response.message = "Motors enabled"
                
            elif not request.enable:
                # Disable - stop first!
                self.bot.set_car_motion(0, 0, 0)
                self.motors_enabled = False
                response.success = True
                response.message = "Motors disabled"
                
            else:
                # Can't enable - emergency stop active
                response.success = False
                response.message = "Emergency stop active"
    
    except Exception as e:
        response.success = False
        response.message = f"Error: {str(e)}"
    
    return response
```

### Reset Odometry Service

```python
def _reset_odometry_callback(self, request, response):
    """Reset odometry to zero"""
    try:
        # Reset firmware odometry
        self.bot.reset_odometry()
        
        # Reset covariance accumulators
        self._accumulated_distance = 0.0
        self._accumulated_rotation = 0.0
        
        response.success = True
        response.message = "Odometry reset"
        
    except Exception as e:
        response.success = False
        response.message = f"Reset failed: {e}"
    
    return response
```

---

## 🧹 Cleanup

### Shutdown Sequence

```python
def cleanup(self):
    """Shutdown cleanup"""
    self.get_logger().info("Shutting down...")
    
    if self.hardware_connected and self.bot:
        try:
            # Stop robot
            self.bot.set_car_motion(0, 0, 0)
            
            # Disable auto-report
            self.bot.set_auto_report_state(False, forever=False)
            
        except Exception as e:
            self.get_logger().debug(f'Cleanup error: {e}')
        
        finally:
            # Close serial port
            self.bot.close()
```

**Called from main():**
```python
try:
    executor.spin()
except KeyboardInterrupt:
    pass
finally:
    node.cleanup()  # Always cleanup!
```

---

## 🎯 Key Design Patterns

### 1. Check Early, Return Fast

```python
def callback(self):
    if not condition:
        return  # Guard clause
    
    # Main logic only if valid
```

### 2. Lock Minimal Section

```python
# Bad - hold lock during slow operation
with self._lock:
    result = slow_operation()
    process(result)

# Good - only lock data access
with self._lock:
    data = self.data
result = slow_operation(data)
process(result)
```

### 3. Validate Inputs

```python
vx = max(-limit, min(value, limit))  # Clamp to range
```

### 4. Graceful Degradation

```python
try:
    risky_operation()
except Exception as e:
    log_error(e)
    # Continue operating if possible
```

---

## 📚 Next Steps

Now you understand the hardware node. Next, learn about the low-level driver:

**→ Continue to:** [05-driver-deep-dive.md](05-driver-deep-dive.md)

Or jump to sensor topics:

**→ Or go to:** [06-imu-sensors.md](06-imu-sensors.md)

---

## 💭 Review Questions

1. **Why are there separate locks for state and command time?**
   <details>
   <summary>Click for answer</summary>
   Different variables are accessed by different threads. Separating locks reduces contention and prevents deadlocks.
   </details>

2. **Why check for unchanged odometry before publishing?**
   <details>
   <summary>Click for answer</summary>
   Deduplication saves bandwidth and CPU. Firmware sends at 25Hz, but we publish at 50Hz. Skip duplicates.
   </details>

3. **Why send stop command outside the cmd_time_lock?**
   <details>
   <summary>Click for answer</summary>
   set_car_motion() takes 2ms. Holding the lock would block incoming cmd_vel messages during that time.
   </details>

---

**You now understand the hardware node in detail! 🔍**