# 02 - Hardware Architecture

**How all the pieces fit together**

---

## 🎯 Learning Objectives

After reading this, you will understand:
- The three-file architecture of `orbibot_hardware`
- Why we separate concerns
- The hardware board (ROSMaster) components
- Data flow from software to motors
- The firmware's role

---

## 🏗️ Three-File Architecture

### The Design Philosophy

**Separation of Concerns** - Each file has ONE job:

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORBIBOT_HARDWARE PACKAGE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ hardware_node   │←──→│ rosmaster_driver│←──→│  STM32      │ │
│  │   .py           │    │    .py          │    │ Firmware    │ │
│  │                 │    │                 │    │             │ │
│  │ ROS 2           │    │ Serial Protocol │    │ Motor Ctrl  │ │
│  │ Integration     │    │ Binary Packets  │    │ Sensors     │ │
│  │ Topics/Services │    │ No ROS deps!    │    │ Real-time   │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           ↑                                              │       │
│           │                                              │       │
│           ↓                                              ↓       │
│  ┌─────────────────┐                            Physical Robot │
│  │ system_monitor  │                            Motors/IMU/etc  │
│  │    .py          │                                            │
│  │                 │                                            │
│  │ CPU/RAM/Disk    │                                            │
│  │ Extra monitoring│                                            │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### File Responsibilities

| File | Responsibility | Why Separate? |
|------|---------------|---------------|
| `hardware_node.py` | ROS 2 integration | Can change ROS version without touching hardware code |
| `rosmaster_driver.py` | Serial communication | Can use driver in non-ROS projects |
| `system_monitor.py` | System health | Optional - can disable if not needed |

---

## 🔌 The Physical Hardware

### ROSMaster Board Components

```
┌─────────────────────────────────────────┐
│        ROSMaster Expansion Board        │
│              (Yahboom V3)               │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────┐  ┌───────────────┐  │
│  │  STM32F103    │  │  ICM-20948    │  │
│  │ Microcontroller│  │  6-axis IMU   │  │
│  │               │  │               │  │
│  │ • Main brain  │  │ • Accelerometer│ │
│  │ • 100Hz control│ │ • Gyroscope   │  │
│  │ • Serial comm │  │ • (no mag)   │  │
│  └───────────────┘  └───────────────┘  │
│                                         │
│  ┌───────────────┐  ┌───────────────┐  │
│  │ Motor Drivers │  │  Encoders     │  │
│  │  (4 channels) │  │  (4 channels) │  │
│  │               │  │               │  │
│  │ • PWM control │  │ • 1320 ticks/rev│ │
│  │ • Current sensing│ │ • Quadrature  │ │
│  └───────────────┘  └───────────────┘  │
│                                         │
│  ┌───────────────┐  ┌───────────────┐  │
│  │    Battery    │  │    Serial     │  │
│  │    Monitor    │  │    (USB)      │  │
│  │               │  │               │  │
│  │ • 3S LiPo     │  │ • 115200 baud │  │
│  │ • 10.5-12.6V  │  │ • Protocol    │  │
│  └───────────────┘  └───────────────┘  │
│                                         │
└─────────────────────────────────────────┘
```

### Key Specifications

| Component | Spec | Notes |
|-----------|------|-------|
| **Microcontroller** | STM32F103RCT6 | 72MHz ARM Cortex-M3 |
| **IMU** | ICM-20948 | Accel + gyro (its magnetometer is not used) |
| **Motors** | 4× DC with encoders | Mecanum wheel configuration |
| **Encoder Resolution** | 1320 ticks/rev | 11 PPR × 30:1 gearbox × 4 quadrature |
| **Serial Speed** | 115200 baud | ~14 KB/s data rate |
| **Control Rate** | 100 Hz | 10ms PID loop |
| **Sensor Rate** | 50 Hz | 20ms IMU/encoder updates |

---

## 🔄 Data Flow: Command Path

### From Your Brain to Motor Movement

```
YOU want to move forward
        ↓
┌─────────────────────────────────────────────────────────────┐
│ SOFTWARE LAYER                                              │
├─────────────────────────────────────────────────────────────┤
│ Controller node (teleop)                                    │
│   Interprets joystick                                       │
│   Creates Twist message                                     │
│   Publishes to /cmd_vel                                     │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ HARDWARE_NODE.PY                                            │
├─────────────────────────────────────────────────────────────┤
│ cmd_vel_callback() receives message                         │
│   ↓                                                         │
│ Extracts: vx, vy, vz (velocity commands)                    │
│   ↓                                                         │
│ Validates: within limits (max 1.0 m/s)                      │
│   ↓                                                         │
│ Calls: bot.set_car_motion(vx, vy, vz)                       │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ ROSMASTER_DRIVER.PY                                         │
├─────────────────────────────────────────────────────────────┤
│ set_car_motion()                                            │
│   ↓                                                         │
│ Convert: m/s → mm/s (multiply by 1000)                      │
│   ↓                                                         │
│ Build packet: [0xFF, 0xFC, 0x08, 0x12, vx_h, vx_l, ...]     │
│   ↓                                                         │
│ Send: ser.write(packet)                                     │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ SERIAL CABLE                                                │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ STM32 FIRMWARE                                              │
├─────────────────────────────────────────────────────────────┤
│ Parse packet                                                │
│   ↓                                                         │
│ Mecanum kinematics:                                         │
│   FL_speed = vx + vy + wz×(lx+ly)                           │
│   FR_speed = vx - vy - wz×(lx+ly)                           │
│   BL_speed = vx - vy + wz×(lx+ly)                           │
│   BR_speed = vx + vy - wz×(lx+ly)                           │
│   ↓                                                         │
│ PID control for each wheel                                  │
│   ↓                                                         │
│ Set PWM duty cycle                                          │
│   ↓                                                         │
│ MOTORS SPIN!                                                │
└─────────────────────────────────────────────────────────────┘
```

**Time from command to motion: ~5-10 milliseconds**

---

## 🔄 Data Flow: Sensor Path

### From Physical World to Navigation

```
Robot is moving
        ↓
┌─────────────────────────────────────────────────────────────┐
│ PHYSICAL SENSORS                                            │
├─────────────────────────────────────────────────────────────┤
│ Encoders: Counting wheel rotation                           │
│   "Motor 1: +100 ticks"                                     │
│                                                             │
│ IMU: Measuring orientation                                  │
│   "Roll: 0°, Pitch: 0°, Yaw: 45°"                          │
│                                                             │
│ Battery: Measuring voltage                                  │
│   "11.8V"                                                   │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ STM32 FIRMWARE @ 100Hz                                      │
├─────────────────────────────────────────────────────────────┤
│ Read encoders                                               │
│ Integrate position: x += vx × dt                            │
│ Update orientation from IMU                                 │
│   ↓                                                         │
│ Build packets: [0xFF, 0xFC, 0x18, 0x0F, x_h, x_l, y_h...]   │
│   ↓                                                         │
│ Send via serial                                             │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ ROSMASTER_DRIVER.PY (receive thread)                        │
├─────────────────────────────────────────────────────────────┤
│ Parse incoming packets                                      │
│ Update internal variables:                                  │
│   self._odom_x = x                                          │
│   self._odom_y = y                                          │
│   self._yaw = yaw                                           │
│   self._battery = voltage                                   │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ HARDWARE_NODE.PY @ 50Hz (timer callback)                    │
├─────────────────────────────────────────────────────────────┤
│ sensor_callback()                                           │
│   ↓                                                         │
│ Get data: bot.get_firmware_odometry()                       │
│   ↓                                                         │
│ Build Odometry message                                      │
│ Build Imu message                                           │
│   ↓                                                         │
│ Publish: /odom, /imu/data, /orbibot/system_status           │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ OTHER NODES                                                 │
├─────────────────────────────────────────────────────────────┤
│ control_manager: Uses /odom for position tracking           │
│ navigation: Plans paths using position                      │
│ RViz: Visualizes robot pose                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Firmware vs Software Responsibilities

### Why Firmware Handles Kinematics?

| Task | Where | Why? |
|------|-------|------|
| **Mecanum kinematics** | Firmware (STM32) | Real-time guarantee, 100Hz |
| **PID control** | Firmware (STM32) | Fast loop, hardware PWM |
| **Encoder integration** | Firmware (STM32) | 100Hz accurate timing |
| **IMU reading** | Firmware (STM32) | Hardware SPI interface |
| **Odometry calculation** | Firmware (STM32) | Accurate integration |
| **Protocol encoding** | Driver (Python) | Flexibility, easy to modify |
| **ROS integration** | Node (Python) | ROS 2 specific |
| **Safety monitoring** | Node (Python) | Complex logic easier in Python |

### Benefits of This Split

```
✅ Firmware (STM32):
   - Real-time guaranteed (no OS delays)
   - 100Hz control loop (very fast)
   - Hardware-level timing accuracy
   - Works independently

✅ Software (Python/ROS):
   - Easier to develop and debug
   - Rich ROS 2 ecosystem
   - Complex algorithms (SLAM, planning)
   - Easy to update without reflashing
```

---

## 🔒 Safety Architecture

### Multiple Safety Layers

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Application (Navigation)                           │
│   - Obstacle avoidance                                      │
│   - Path planning                                           │
└─────────────────────────────────────────────────────────────┘
        ↓ (sends commands)
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: hardware_node (Software)                           │
│   - Command timeout (stop if no commands)                   │
│   - Velocity limits (clamp to safe values)                  │
│   - Battery monitoring (emergency stop if low)              │
│   - Motors must be explicitly enabled                       │
└─────────────────────────────────────────────────────────────┘
        ↓ (validates commands)
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: rosmaster_driver (Protocol)                        │
│   - Packet validation (checksum)                            │
│   - Serial connection monitoring                            │
│   - Automatic reconnection                                  │
└─────────────────────────────────────────────────────────────┘
        ↓ (sends packets)
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: STM32 Firmware (Hardware)                          │
│   - Over-current protection                                 │
│   - PWM limits (motor protection)                           │
│   - Watchdog timer (reset if frozen)                        │
│   - Emergency stop pin                                      │
└─────────────────────────────────────────────────────────────┘
```

### Safety Features in hardware_node

| Feature | How It Works | Default |
|---------|--------------|---------|
| **Command Timeout** | Stop motors if no /cmd_vel for 2s | 2.0 seconds |
| **Velocity Limits** | Clamp to max_velocity | 1.0 m/s |
| **Battery Protection** | Emergency stop if <10.5V | 10.5V threshold |
| **Motor Enable** | Must explicitly enable motors | Disabled on startup |
| **Emergency Stop** | Software flag + hardware pin | Cleared on start |

---

## 📁 Configuration Architecture

### Parameter Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ DEFAULT VALUES (in code)                                    │
│   max_velocity = 1.0                                        │
│   cmd_timeout = 2.0                                         │
│   battery_low = 11.0                                        │
└─────────────────────────────────────────────────────────────┘
        ↓ overridden by
┌─────────────────────────────────────────────────────────────┐
│ CONFIG FILE (hardware_params.yaml)                          │
│   control:                                                  │
│     max_velocity: 0.8      # Safer limit                    │
│     cmd_timeout: 1.5       # Faster stop                    │
└─────────────────────────────────────────────────────────────┘
        ↓ overridden by
┌─────────────────────────────────────────────────────────────┐
│ LAUNCH ARGUMENTS                                            │
│   ros2 launch ... max_velocity:=0.5                        │
└─────────────────────────────────────────────────────────────┘
```

### Why This Hierarchy?

1. **Code defaults** - Safe values if nothing else set
2. **YAML config** - Robot-specific settings
3. **Launch args** - Runtime overrides for testing

---

## 🧪 Visualizing the Architecture

### Running System View

```bash
# Terminal 1: Launch hardware
ros2 launch orbibot_hardware hardware.launch.py

# Terminal 2: View node graph
ros2 run rqt_graph rqt_graph

# You should see:
#   [teleop_node] --/cmd_vel--> [hardware_node]
#   [hardware_node] --/odom--> [control_manager]
#   [hardware_node] --/imu/data--> [filter_node]
```

### Node Connections

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ teleop_node  │─cmd_vel→│ hardware_node│──odom──→│control_manager│
└──────────────┘         │              │         └──────────────┘
                         │              │         ┌──────────────┐
                         │              │─imu/data→│  ekf_node   │
                         │              │         └──────────────┘
                         │              │         ┌──────────────┐
                         │              │─system──→│ system_monitor│
                         └──────────────┘  status   └──────────────┘
                                │
                                │ serial
                                ↓
                         ┌──────────────┐
                         │   STM32      │
                         │  Firmware    │
                         └──────────────┘
                                │
                                │ PWM/sensors
                                ↓
                         ┌──────────────┐
                         │    Robot     │
                         │   Hardware   │
                         └──────────────┘
```

---

## 🎯 Key Takeaways

1. **Three files, three responsibilities** - Clean separation makes code maintainable
2. **Firmware handles real-time** - STM32 does fast control (100Hz)
3. **Software handles integration** - ROS 2 and complex logic in Python
4. **Driver is reusable** - Can use rosmaster_driver without ROS
5. **Safety is layered** - Multiple independent safety checks
6. **Configuration is flexible** - Defaults → YAML → launch args

---

## 📚 Next Steps

Now you understand the architecture. Next, dive into how serial communication works:

**→ Continue to:** [03 - Serial Communication](03-serial-communication.md)

---

## 💭 Review Questions

1. **Why is kinematics done in firmware rather than software?**
   <details>
   <summary>Click for answer</summary>
   Firmware provides real-time guarantees (100Hz hard timing), while Python has variable delays due to the operating system.
   </details>

2. **What are the three main files and their jobs?**
   <details>
   <summary>Click for answer</summary>
   1. hardware_node.py - ROS 2 integration
   2. rosmaster_driver.py - Serial communication
   3. system_monitor.py - System health monitoring
   </details>

3. **Why must motors be explicitly enabled?**
   <details>
   <summary>Click for answer</summary>
   Safety - prevents accidental movement on startup. Robot won't move until you specifically enable motors via service call.
   </details>

---

**You now understand the big picture! 🏗️**