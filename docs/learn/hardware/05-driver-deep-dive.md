---
title: "05 - Driver Deep Dive"
type: learn
area: hardware
package: orbibot_hardware
tags:
  - learn
  - hardware
---

# 05 - Driver Deep Dive

**Understanding rosmaster_driver.py - the serial protocol layer**

---

## 🎯 Learning Objectives

After reading this, you will understand:
- The driver's responsibilities
- How packets are built and parsed
- Thread safety in serial communication
- The receive thread architecture

---

## 📁 File Overview

```python
# File: src/orbibot_hardware/orbibot_hardware/rosmaster_driver.py
# Lines: ~520
# Purpose: Low-level serial communication driver
# Key: NO ROS DEPENDENCIES - can be used standalone!
```

### Why No ROS?

```
Benefits:
✅ Can use in any Python project
✅ Easy to test without ROS installed
✅ Clear separation of concerns
✅ Could port to other frameworks easily
```

---

## 🏗️ Class Structure

### The Rosmaster Class

```python
class Rosmaster(object):
    """
    Serial driver for Yahboom ROSMaster board.
    Handles packet encoding/decoding, maintains sensor state.
    """
```

### Key Attributes

```python
# Serial connection
self.ser = serial.Serial(com, 115200, timeout=0.1)

# State flags
self._running = True           # Controls receive thread
self._uart_state = 0           # Thread status
self._auto_report_enabled = False

# Sensor data (protected by locks)
self._odom_x = 0.0             # Position X (meters)
self._odom_y = 0.0             # Position Y (meters)
self._odom_theta = 0.0         # Heading (radians)

self._ax, self._ay, self._az = 0.0, 0.0, 0.0  # Accelerometer
self._gx, self._gy, self._gz = 0.0, 0.0, 0.0  # Gyroscope

self._encoder_m1 = 0           # Motor 1 encoder count
# ... etc for all 4 motors

# Locks
self._data_lock = threading.Lock()    # Protects sensor data
self._write_lock = threading.Lock()   # Protects serial writes
```

---

## 🔌 Serial Connection Setup

### Constructor

```python
def __init__(self, car_type=1, com="/dev/motordriver", delay=.002, debug=False):
    # Store settings
    self._com_port = com
    self._delay_time = delay
    self._debug = debug
    self._car_type = car_type
    
    # Open serial port
    try:
        self.ser = serial.Serial(com, 115200, timeout=0.1)
    except serial.SerialException as e:
        raise RuntimeError(f"Failed to open serial port {com}: {e}")
    
    # Initialize all data to zero
    self._clear_data()
    
    # Print status
    if self.ser.is_open:
        print("Rosmaster Serial Opened! Baudrate=115200")
```

### Protocol Constants

```python
# Packet structure
SERIAL_HEAD = 0xFF          # Start byte
SERIAL_DEVICE_ID = 0xFC     # Device identifier
SERIAL_COMPLEMENT = 257 - SERIAL_DEVICE_ID  # For checksum

# Function codes (commands TO firmware)
FUNC_AUTO_REPORT = 0x01
FUNC_BEEP = 0x02
FUNC_MOTION = 0x12
FUNC_SET_MOTOR_PID = 0x13
FUNC_SET_YAW_PID = 0x14
FUNC_SET_MOTOR_PID_MULTILEVEL = 0x18
FUNC_RESET_ODOM = 0x09

# Function codes (data FROM firmware)
FUNC_REPORT_SPEED = 0x0A
FUNC_REPORT_IMU_ATT = 0x0C
FUNC_REPORT_ENCODER = 0x0D
FUNC_REPORT_ICM_RAW = 0x0E
FUNC_REPORT_ODOM = 0x15
```

---

## 📤 Sending Commands

### Motion Command (set_car_motion)

```python
def set_car_motion(self, v_x, v_y, v_z):
    """
    Send velocity command to robot.
    v_x, v_y: linear velocity in m/s (-1.0 to 1.0)
    v_z: angular velocity in rad/s (-5 to 5)
    """
    try:
        # Step 1: Convert to mm/s (integers)
        vx_mm = int(v_x * 1000)
        vy_mm = int(v_y * 1000)
        vz_mm = int(v_z * 1000)
        
        # Step 2: Pack into bytes (little-endian)
        # 'h' = signed short (2 bytes)
        vx_bytes = struct.pack('h', vx_mm)
        vy_bytes = struct.pack('h', vy_mm)
        vz_bytes = struct.pack('h', vz_mm)
        
        # Step 3: Build packet
        cmd = [
            SERIAL_HEAD,           # 0xFF
            SERIAL_DEVICE_ID,      # 0xFC
            0x0B,                  # Length (11 bytes - 1)
            FUNC_MOTION,           # 0x12
            self._car_type,        # 0x07 (OrbiBot)
            vx_bytes[0], vx_bytes[1],  # vx low, high
            vy_bytes[0], vy_bytes[1],  # vy low, high
            vz_bytes[0], vz_bytes[1],  # vz low, high
        ]
        
        # Step 4: Calculate checksum
        checksum = sum(cmd, SERIAL_COMPLEMENT) & 0xFF
        cmd.append(checksum)
        
        # Step 5: Send with lock protection
        with self._write_lock:
            self.ser.write(cmd)
        
        # Step 6: Small delay for firmware processing
        time.sleep(self._delay_time)  # Default 2ms
        
    except serial.SerialException as e:
        print(f'Serial error: {e}')
```

### struct.pack Explained

```python
import struct

# 'h' = signed short (16-bit integer, -32768 to 32767)
value = 500
bytes_data = struct.pack('h', value)
# Result: b'\xf4\x01' (little-endian)

# Little-endian: least significant byte first
# 500 = 0x01F4 → [0xF4, 0x01]

# Unpacking (reverse)
value = struct.unpack('h', b'\xf4\x01')[0]
# Result: 500
```

---

## 📥 Receiving Data

### The Receive Thread

```python
def create_receive_threading(self):
    """Start background thread for receiving data"""
    if self._uart_state == 0:
        thread = threading.Thread(
            target=self._receive_data,
            name="serial_receive"
        )
        thread.daemon = True  # Dies when main program exits
        thread.start()
        self._uart_state = 1
        time.sleep(0.05)  # Let thread start
```

### State Machine Parser

```python
def _receive_data(self):
    """Main receive loop - runs in background thread"""
    self.ser.reset_input_buffer()
    
    while self._running:
        try:
            # Read one byte at a time
            data = self.ser.read(1)
            if not data:
                continue
            
            byte = data[0]
            
            # State machine for packet parsing
            if byte == SERIAL_HEAD:  # 0xFF found
                # Read rest of header
                device_id = self.ser.read(1)
                if not device_id or device_id[0] != SERIAL_DEVICE_ID - 1:
                    continue
                
                # Read length and function
                length_data = self.ser.read(1)
                func_data = self.ser.read(1)
                if not length_data or not func_data:
                    continue
                
                ext_len = length_data[0]
                ext_func = func_data[0]
                
                # Read data payload
                data_len = ext_len - 2
                ext_data = self.ser.read(data_len)
                if len(ext_data) < data_len:
                    continue  # Incomplete packet
                
                # Read checksum
                checksum_data = self.ser.read(1)
                if not checksum_data:
                    continue
                
                rx_checksum = checksum_data[0]
                
                # Verify checksum
                calc_checksum = (ext_len + ext_func + sum(ext_data)) & 0xFF
                if calc_checksum != rx_checksum:
                    if self._debug:
                        print("Checksum error!")
                    continue
                
                # Parse the data
                self._parse_data(ext_func, ext_data)
                
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._reconnect_serial()
```

---

## 🔍 Data Parsing

### Odometry Parsing

```python
def _parse_data(self, ext_type, ext_data):
    """Parse received packet based on type"""
    
    if ext_type == FUNC_REPORT_ODOM:
        # Data format: 6× int32 (little-endian)
        # [x, y, theta, vx, vy, omega] in mm, mrad, mm/s, mrad/s
        if len(ext_data) < 24:
            return
        
        # Unpack all 6 values at once
        vals = struct.unpack('<6i', ext_data[:24])
        
        with self._data_lock:
            self._odom_x = vals[0] / 1000.0       # mm → m
            self._odom_y = vals[1] / 1000.0       # mm → m
            self._odom_theta = vals[2] / 1000.0   # mrad → rad
            self._odom_vx = vals[3] / 1000.0      # mm/s → m/s
            self._odom_vy = vals[4] / 1000.0      # mm/s → m/s
            self._odom_omega = vals[5] / 1000.0   # mrad/s → rad/s
    
    elif ext_type == FUNC_REPORT_ICM_RAW:
        # Raw IMU data: 9× int16
        # [gx, gy, gz, ax, ay, az, mx, my, mz]
        if len(ext_data) < 18:
            return
        
        with self._data_lock:
            # Gyroscope (rad/s) - pre-scaled by firmware
            self._gx = struct.unpack('h', ext_data[0:2])[0] / 1000.0
            self._gy = struct.unpack('h', ext_data[2:4])[0] / 1000.0
            self._gz = struct.unpack('h', ext_data[4:6])[0] / 1000.0
            
            # Accelerometer (m/s²)
            self._ax = struct.unpack('h', ext_data[6:8])[0] / 1000.0
            self._ay = struct.unpack('h', ext_data[8:10])[0] / 1000.0
            self._az = struct.unpack('h', ext_data[10:12])[0] / 1000.0
            
            # Magnetometer (uT)
            self._mx = struct.unpack('h', ext_data[12:14])[0] / 1000.0
            self._my = struct.unpack('h', ext_data[14:16])[0] / 1000.0
            self._mz = struct.unpack('h', ext_data[16:18])[0] / 1000.0
    
    elif ext_type == FUNC_REPORT_ENCODER:
        # Encoder counts: 4× int32
        if len(ext_data) < 16:
            return
        
        with self._data_lock:
            self._encoder_m1 = struct.unpack('i', ext_data[0:4])[0]
            self._encoder_m2 = struct.unpack('i', ext_data[4:8])[0]
            self._encoder_m3 = struct.unpack('i', ext_data[8:12])[0]
            self._encoder_m4 = struct.unpack('i', ext_data[12:16])[0]
```

---

## 🔒 Thread Safety

### Why Locks Matter

```
Thread 1 (Main):           Thread 2 (Receive):
                           Read encoder: 1000
Read encoder: 1000
                           Read encoder: 1001
Use encoder: 1000          Update encoder: 1001

Inconsistent! Thread 1 saw 1000 but 
firmware had already sent 1001.
```

### Lock Usage Pattern

```python
# In receive thread (writer)
with self._data_lock:
    self._odom_x = new_x
    self._odom_y = new_y

# In main thread (reader)
with self._data_lock:
    x = self._odom_x
    y = self._odom_y
# Use x, y after releasing lock

# Guaranteed consistent read!
```

### Write Lock

```python
# Multiple threads might try to send commands
with self._write_lock:
    self.ser.write(packet1)

with self._write_lock:
    self.ser.write(packet2)

# Packets can't interleave - always complete before next starts
```

---

## 🔄 Auto-Report Mode

### What is Auto-Report?

```
Instead of constantly asking "What's the IMU data?":
  Request → Response (polling)

Firmware continuously sends:
  → IMU data
  → Odometry
  → Encoders
  → Battery
  
  Just read from buffer - no waiting!
```

### Enabling Auto-Report

```python
def set_auto_report_state(self, enable, forever=False):
    """
    Enable/disable automatic data transmission.
    
    Args:
        enable: True to enable, False to disable
        forever: True = save to flash (permanent)
    """
    state1 = 1 if enable else 0
    state2 = 0x5F if forever else 0  # Magic number for "permanent"
    
    cmd = [SERIAL_HEAD, SERIAL_DEVICE_ID, 0x05, 
           FUNC_AUTO_REPORT, state1, state2]
    checksum = sum(cmd, SERIAL_COMPLEMENT) & 0xFF
    cmd.append(checksum)
    
    with self._write_lock:
        self.ser.write(cmd)
    
    self._auto_report_enabled = enable
    time.sleep(self._delay_time)
```

---

## 🆘 Reconnection Handling

### Automatic Reconnect

```python
def _reconnect_serial(self, max_retries=10, retry_delay=1.0):
    """Attempt to reconnect after disconnect"""
    for attempt in range(max_retries):
        if not self._running:
            return False
        
        try:
            # Close old connection
            try:
                self.ser.close()
            except:
                pass
            
            time.sleep(retry_delay)
            
            # Try to reopen
            self.ser = serial.Serial(self._com_port, 115200, timeout=0.1)
            self.ser.reset_input_buffer()
            
            # Restore auto-report if it was enabled
            if self._auto_report_enabled:
                self.set_auto_report_state(True)
            
            print(f"Reconnected on attempt {attempt + 1}")
            return True
            
        except serial.SerialException as e:
            print(f"Reconnect attempt {attempt + 1} failed: {e}")
    
    print("Failed to reconnect")
    return False
```

---

## 📤 Getter Methods

### Safe Data Access

```python
def get_firmware_odometry(self):
    """Get position and velocity"""
    with self._data_lock:
        return (self._odom_x, self._odom_y, self._odom_theta,
                self._odom_vx, self._odom_vy, self._odom_omega)

def get_accelerometer_data(self):
    """Get accelerometer (m/s²)"""
    with self._data_lock:
        return (self._ax, self._ay, self._az)

def get_gyroscope_data(self):
    """Get gyroscope (rad/s)"""
    with self._data_lock:
        return (self._gx, self._gy, self._gz)

def get_motor_encoder(self):
    """Get encoder counts"""
    with self._data_lock:
        return (self._encoder_m1, self._encoder_m2, 
                self._encoder_m3, self._encoder_m4)
```

---

## 🎯 Key Takeaways

1. **Driver is standalone** - No ROS dependencies
2. **Two threads** - Main thread sends, receive thread reads
3. **Locks protect shared data** - Thread safety is critical
4. **Auto-report mode** - Firmware pushes data continuously
5. **Automatic reconnection** - Handles disconnects gracefully
6. **Little-endian binary** - Fast, compact protocol

---

## 📚 Next Steps

Learn about the sensors themselves:

**→ Continue to:** [[02-imu-sensors]]

---

## 💭 Review Questions

1. **Why does the driver use locks?**
   <details>
   <summary>Click for answer</summary>
   Multiple threads access shared data (main thread reads, receive thread writes). Locks prevent race conditions.
   </details>

2. **What is auto-report mode?**
   <details>
   <summary>Click for answer</summary>
   Firmware continuously sends sensor data without being asked. More efficient than polling for each value.
   </details>

3. **Why convert m/s to mm/s when sending?**
   <details>
   <summary>Click for answer</summary>
   Firmware uses integers for efficiency. 0.5 m/s = 500 mm/s fits in 16-bit integer with good precision.
   </details>

---

**You now understand the low-level driver! 🔌**