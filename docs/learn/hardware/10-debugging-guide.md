---
title: "10 - Debugging Guide"
type: learn
area: hardware
package: orbibot_hardware
tags:
  - learn
  - hardware
---

# 10 - Debugging Guide

**Troubleshooting techniques for hardware issues**

---

## 🎯 Learning Objectives

After reading this, you will know how to:
- Diagnose common hardware connection problems
- Use ROS 2 debugging tools
- Interpret error messages
- Fix common issues

---

## 🔍 Diagnostic Tools

### 1. Comprehensive Diagnostic Script

```bash
# Run the built-in diagnostic
cd ~/orbibot_ws/src/orbibot_hardware/scripts
python3 comprehensive_diagnostic.py
```

**What it checks:**
- ✅ Serial port access
- ✅ Hardware communication
- ✅ IMU data reception
- ✅ Motor command sending
- ✅ Battery voltage reading

### 2. Manual Diagnostics

```bash
# Check serial port exists
ls -la /dev/motordriver

# Check port permissions
ls -la /dev/ttyUSB*  # or /dev/ttyACM*

# Test direct serial access
screen /dev/motordriver 115200
# (Press Ctrl+A then K to quit)
```

---

## 🚨 Common Issues and Solutions

### Issue 1: "Permission Denied" on Serial Port

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/dev/motordriver'
```

**Cause:** User not in `dialout` group

**Solution:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER

# Apply changes (logout and login, or reboot)
# Then verify:
groups  # Should show 'dialout'
```

**Alternative (temporary):**
```bash
sudo chmod 666 /dev/motordriver
```

---

### Issue 2: "Rosmaster Driver Not Available"

**Symptom:**
```
[ERROR] rosmaster_driver not available
[ERROR] Hardware initialization failed
```

**Diagnosis Steps:**

```bash
# 1. Check Python can import it
python3 -c "from orbibot_hardware import rosmaster_driver; print('OK')"

# 2. If error, rebuild package
cd ~/orbibot_ws
colcon build --packages-select orbibot_hardware
source install/setup.bash

# 3. Check PYTHONPATH
echo $PYTHONPATH
# Should include orbibot_hardware path

# 4. Try again
python3 -c "from orbibot_hardware import rosmaster_driver; print('OK')"
```

---

### Issue 3: Serial Port Not Found

**Symptom:**
```
RuntimeError: Failed to open serial port /dev/motordriver
```

**Diagnosis:**

```bash
# 1. List all serial devices
ls -la /dev/tty*

# 2. Check which device appears when plugging in USB
# (Unplug, run ls, plug in, run ls again - compare)

# 3. Check udev rules
cat /etc/udev/rules.d/99-orbibot.rules
# Should contain:
# SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ... SYMLINK+="motordriver"

# 4. Reload rules if needed
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Workaround (use actual device):**
```bash
# Launch with specific port
ros2 launch orbibot_hardware hardware.launch.py serial_port:=/dev/ttyUSB0
```

---

### Issue 4: Motors Don't Move

**Checklist:**

```bash
# 1. Are motors enabled?
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"
# Response should be: success: true

# 2. Check battery voltage
ros2 topic echo /orbibot/system_status --once
# battery_voltage should be > 11.0V

# 3. Check for emergency stop
ros2 topic echo /orbibot/safety_status --once
# emergency_stop should be false

# 4. Is hardware connected?
ros2 topic echo /orbibot/system_status --once
# hardware_ok should be true

# 5. Send test command and watch
ros2 topic echo /cmd_vel  # Terminal 1
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"  # Terminal 2
```

**Common Fixes:**

| Problem | Fix |
|---------|-----|
| Battery < 10.5V | Charge battery |
| emergency_stop = true | Clear emergency condition |
| hardware_ok = false | Check serial connection |
| Motors make noise but don't move | Mechanical issue - check wheels |

---

### Issue 5: No Sensor Data

**Symptom:** `/odom`, `/imu/data` topics empty

**Diagnosis:**

```bash
# Check topic exists
ros2 topic list | grep -E "(odom|imu)"

# Check publish rate
ros2 topic hz /odom
# Should be ~20-25 Hz

# Check topic info
ros2 topic info /odom
# Should show publishers

# Echo topic
ros2 topic echo /odom --once
```

**Possible Causes:**

1. **Firmware not sending data**
   ```bash
   # Check auto-report enabled
   # (Look in launch logs for "auto-report state: True")
   ```

2. **Serial communication broken**
   ```bash
   # Check for errors in node logs
   ros2 node logs /orbibot_hardware_node
   ```

3. **Wrong topic name**
   ```bash
   # Check actual topic names
   ros2 topic list
   ```

---

## 🛠️ Debugging Commands

### View Node Status

```bash
# List nodes
ros2 node list

# Get node info
ros2 node info /orbibot_hardware_node

# View parameters
ros2 param list /orbibot_hardware_node
ros2 param get /orbibot_hardware_node control.max_velocity
```

### Monitor Topics

```bash
# Watch all hardware topics
ros2 topic list | grep orbibot | xargs -I {} sh -c 'echo "=== {} ===" && ros2 topic echo {} --once'

# Check topic frequencies
ros2 topic hz /odom
ros2 topic hz /imu/data
ros2 topic hz /orbibot/system_status

# Plot data in real-time
ros2 run rqt_plot rqt_plot /odom/pose/pose/position/x /odom/pose/pose/position/y
```

### Test Services

```bash
# Test motor enable
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Test reset odometry
ros2 service call /orbibot/reset_odometry orbibot_msgs/srv/ResetOdometry "{}"

# List all services
ros2 service list | grep orbibot
```

### Check Logs

```bash
# View all logs
ros2 node logs /orbibot_hardware_node

# Filter for errors
ros2 node logs /orbibot_hardware_node | grep -i error

# View with timestamp
ros2 node logs /orbibot_hardware_node --format "[{severity}] [{time}] {message}"
```

---

## 📝 Log Message Reference

### Normal Messages

| Message | Meaning |
|---------|---------|
| `OrbiBot Hardware Node started` | Node initialized successfully |
| `ROSMaster connected successfully` | Serial communication established |
| `Motors enabled` | Motor enable service called successfully |
| `Command timeout - stopping robot` | Safety feature working (no commands received) |

### Warning Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `Low battery: 11.0V` | Battery getting low | Charge soon |
| `Firmware odometry stale` | No data from firmware | Check serial connection |
| `max_velocity exceeds safe limit` | Config error | Fix parameter |
| `Motion command failed` | Serial error | Check connection |

### Error Messages

| Message | Meaning | Action |
|---------|---------|--------|
| `Hardware init failed` | Can't connect to board | Check serial port, permissions |
| `rosmaster_driver not available` | Import error | Rebuild package |
| `Critical battery - emergency stop!` | Battery too low | Charge immediately |
| `Serial error in receive thread` | Communication lost | Check cable, reconnect |

---

## 🔬 Advanced Debugging

### Add Debug Prints

Edit `hardware_node.py`:

```python
def _cmd_vel_callback(self, msg: Twist):
    # Add debug logging
    self.get_logger().info(f"Received cmd_vel: vx={msg.linear.x}, vy={msg.linear.y}")
    
    # ... rest of code
    
    self.get_logger().info(f"Sending to firmware: vx={vx}, vy={vy}")
    self.bot.set_car_motion(vx, vy, vz)
```

Rebuild and test:
```bash
colcon build --packages-select orbibot_hardware
ros2 launch orbibot_hardware hardware.launch.py
```

### Enable Driver Debug Mode

```python
# In hardware_node.py, change:
self.bot = rosmaster_driver.Rosmaster(
    car_type=rosmaster_driver.CARTYPE_ORBIBOT,
    com=self.serial_port,
    debug=True  # Enable debug prints
)
```

### Monitor Serial Traffic

```python
# Create file: serial_sniffer.py
import serial

ser = serial.Serial('/dev/motordriver', 115200)
print("Sniffing...")

while True:
    byte = ser.read(1)
    if byte:
        print(f"{byte[0]:02X}", end=" ")
        if byte[0] == 0xFF:
            print("\n---")
```

---

## 🎯 Debugging Workflow

### Step-by-Step Problem Solving

```
1. OBSERVE
   - What exactly is happening?
   - What should be happening?
   - When did it start?

2. GATHER INFO
   - Check logs: ros2 node logs
   - Check topics: ros2 topic list/echo/hz
   - Check services: ros2 service list/call

3. ISOLATE
   - Is it a ROS issue? (topic problems)
   - Is it a serial issue? (connection problems)
   - Is it a firmware issue? (no data)

4. TEST COMPONENTS
   - Test serial: screen /dev/motordriver
   - Test topics: ros2 topic pub
   - Test services: ros2 service call

5. FIX AND VERIFY
   - Apply fix
   - Test again
   - Monitor for recurrence
```

---

## 📋 Pre-Flight Checklist

Before running robot:

```bash
# ☐ Hardware Check
ros2 launch orbibot_hardware hardware.launch.py
# Watch for "ROSMaster connected successfully"

# ☐ Battery Check
ros2 topic echo /orbibot/system_status --once
# Verify battery_voltage > 11.0

# ☐ Enable Motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# ☐ Test Movement (GENTLY)
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
# Robot should move slightly forward

# ☐ Check Sensors
ros2 topic hz /odom        # Should be ~20Hz
ros2 topic hz /imu/data    # Should be ~50Hz

# ☐ Safety Test
# Stop sending commands, wait 3 seconds
# Robot should stop (timeout protection)
```

---

## 🆘 Getting Help

If stuck:

1. **Check this guide** - Most common issues covered here
2. **Check hardware-issue.md** - Known bugs and workarounds
3. **Run diagnostic script** - comprehensive_diagnostic.py
4. **Collect info:**
   ```bash
   # Create debug report
   echo "=== Node List ===" > debug_report.txt
   ros2 node list >> debug_report.txt
   echo "=== Topic List ===" >> debug_report.txt
   ros2 topic list >> debug_report.txt
   echo "=== Last 50 Log Lines ===" >> debug_report.txt
   ros2 node logs /orbibot_hardware_node | tail -50 >> debug_report.txt
   ```

---

## 📚 Next Steps

Practice your skills:

**→ Continue to:** [[11-practical-exercises]]

---

**You now know how to debug hardware issues! 🔧**