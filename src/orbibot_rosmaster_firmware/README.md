# OrbiBot ROSMaster Firmware

Custom firmware for the Yahboom ROSMaster V3.0 expansion board (STM32F103RCT6).
Replaces the closed-source Yahboom firmware with an open, OrbiBot-specific implementation.

**Status:** runs on the robot. It has been tested on the bench, with the wheels off the
ground, on 2026-04-19, 2026-04-28 and 2026-08-03 ([test report](test-report.md)); nothing
has been measured with the robot driving on the floor yet.

This is not a colcon package: it carries a `COLCON_IGNORE` and is built with PlatformIO.

---

## 1. What This Firmware Does

The firmware runs on a **dedicated microcontroller** (STM32, separate from the Raspberry Pi 5)
and handles all **real-time hardware control**:

- Drives 4 mecanum wheel motors with PID speed control at 100Hz
- Reads quadrature encoders and computes wheel odometry
- Reads the ICM-20948 IMU's gyro and accelerometer at 50Hz (its magnetometer is not used since 2026-04-28)
- Monitors battery voltage with safety lockout
- Streams all sensor data to the Raspberry Pi over USB serial

**The firmware is a black box from the ROS 2 perspective.** The `orbibot_hardware` ROS 2 package
talks to it over a serial protocol. You send velocity commands in, you get sensor data out.

```
┌─────────────────────┐   USB Serial (115200)   ┌────────────────────────┐
│  STM32 Firmware      │ ◄─────────────────────► │  Raspberry Pi 5        │
│  (this package)      │                          │  orbibot_hardware node │
│                      │                          │                        │
│  - Motor PID (100Hz) │  ── cmd_vel ──►          │  - /cmd_vel subscriber │
│  - Encoders          │  ◄── odom ────           │  - /odom publisher     │
│  - IMU (50Hz)        │  ◄── imu ─────           │  - /imu publisher      │
│  - Battery monitor   │  ◄── battery ─           │  - /system_status pub  │
└─────────────────────┘                          └────────────────────────┘
```

---

## 2. System Architecture

### Where the firmware sits in the robot stack

```
  Nav2 / SLAM / Teleop (ROS 2)
           │
           ▼
    /cmd_vel (Twist)
           │
           ▼
  orbibot_hardware node (RPi 5)   ◄── ROS 2 layer
           │
       USB Serial                  ◄── binary protocol @ 115200 baud
           │
           ▼
  STM32 Firmware (this package)    ◄── real-time layer (FreeRTOS @ 72MHz)
           │
           ▼
  Motors / Encoders / IMU / Battery
```

### Firmware responsibilities

| Responsibility | Rate | Detail |
|---------------|------|--------|
| Motor PID control | 100Hz | 4 independent PID loops, one per wheel |
| Encoder reading | 100Hz | Quadrature decoding via hardware timers |
| Odometry integration | 100Hz | Midpoint (RK2) method for mecanum kinematics |
| IMU acquisition | 50Hz | ICM-20948: gyro + accel via SPI |
| Attitude estimation | 50Hz | Roll and pitch from the accelerometer, yaw from integrating the gyro |
| Battery monitoring | 1Hz | ADC with EMA filter, safety lockout |
| Data streaming | 50Hz per type | 5 report types, interleaved over serial |

### Communication method

- **Physical**: USB serial (CH340N USB-UART bridge on the board)
- **Linux device**: `/dev/motordriver` (udev symlink) or `/dev/ttyUSB0`
- **Baud rate**: 115200, 8N1
- **Protocol**: Custom binary packets with checksums (ROSMaster-compatible)
- **Direction**: Bidirectional — commands in, sensor data out

---

## 3. Data Flow

### ROS 2 to Firmware (commands)

| What | ROS 2 Topic | Firmware Action |
|------|-------------|-----------------|
| Velocity command | `/cmd_vel` | Mecanum inverse kinematics -> 4 PID targets |
| Enable streaming | _(internal)_ | Start auto-reporting all sensor data |
| Buzzer beep | `/orbibot/beep` | Activate buzzer for N milliseconds |
| Reset odometry | `/orbibot/reset_odometry` | Zero firmware position/heading |
| PID tuning | `/orbibot/pid_params` | Update Kp/Ki/Kd (optionally save to flash) |

### Firmware to ROS 2 (sensor data)

| What | ROS 2 Topic | Rate | Content |
|------|-------------|------|---------|
| Wheel odometry | `/odom` | 50Hz | Position (x, y, theta) + velocity (vx, vy, omega) |
| IMU raw | `/imu/data_raw` | 50Hz | Gyro (rad/s) and accel (m/s^2), a 12-byte packet |
| IMU attitude | `/imu/data` | 50Hz | Roll, pitch, yaw (rad) |
| Encoder counts | `/orbibot/encoders` | 50Hz | Raw tick counts for all 4 motors |
| Battery + speed | `/orbibot/system_status` | 50Hz | Battery voltage, measured wheel speeds |

> All topic names and message types are handled by `orbibot_hardware` — the firmware
> only sends/receives binary serial packets. The ROS 2 node does the translation.

### Data flow diagram

```
                         FIRMWARE (STM32)
                    ┌─────────────────────────┐
  /cmd_vel ──────►  │  Inverse Kinematics      │
                    │  ┌─────┐ ┌─────┐         │
                    │  │PID 1│ │PID 2│ ...      │  ──► Motor PWM
                    │  └──┬──┘ └──┬──┘         │
                    │     │       │             │
  Motor PWM ──────► │  Encoders ──► Forward Kin │  ──► /odom
                    │                           │
  IMU (SPI) ──────► │  Gyro + Accel             │  ──► /imu/data_raw
                    │  Roll/pitch + gyro yaw    │  ──► /imu/data
                    │                           │
  Battery (ADC) ──► │  EMA filter + threshold   │  ──► /system_status
                    └─────────────────────────┘
```

---

## 4. Hardware Mapping

### What's connected to the firmware

| Component | Quantity | What It Does |
|-----------|----------|-------------|
| Mecanum motors | 4 | JGB37-520, 12V, 333 RPM max, 30:1 gear ratio |
| Encoders | 4 | Hall-effect quadrature, 1320 counts per wheel revolution |
| IMU | 1 | ICM-20948: 3-axis gyro + 3-axis accel (its magnetometer is not used) |
| Battery sensor | 1 | ADC with voltage divider (4S LiFePO4, 10.5V–14.6V) |
| Buzzer | 1 | Active buzzer for battery warnings |
| USB serial | 1 | CH340N bridge to Raspberry Pi (115200 baud) |

### Motor positions (mecanum ABBA layout)

```
    Front
  ┌───────────┐
  │ M1    M3  │     M1 = Front-Left
  │ (FL)  (FR)│     M2 = Back-Left
  │           │     M3 = Front-Right
  │ M2    M4  │     M4 = Back-Right
  │ (BL)  (BR)│
  └───────────┘
     Back
```

### Robot geometry

| Parameter | Value |
|-----------|-------|
| Wheel radius | 50mm (100mm diameter mecanum wheels) |
| Track width | 360mm (left-to-right wheel separation) |
| Wheelbase | 260mm (front-to-rear wheel separation) |
| Encoder resolution | 1320 PPR (11 PPR x 30 gear ratio x 4 quadrature) |

> For complete pin mappings and electrical details, see [the ROSMaster board reference](../../docs/hardware/rosmaster-board.md).

---

## 5. Key Firmware Modules

### Motor Control (`task_control.c`)
Runs at 100Hz. Receives velocity commands, computes mecanum inverse kinematics to get
per-wheel target speeds, runs 4 independent PID controllers, and outputs PWM to the
motor drivers. Also integrates odometry at 100Hz using midpoint (RK2) method.

### IMU Acquisition (`task_imu.c`)
Runs at 50Hz. Reads the ICM-20948 over SPI. Computes roll/pitch from the accelerometer
and yaw by integrating the gyro. There is no magnetometer correction: the yaw drifts, and
the ROS 2 side (the EKF, then SLAM or AMCL) corrects it.
All data is cached thread-safely for the communication task to read.

### Communication (`task_communication.c`)
Handles bidirectional serial protocol. Parses incoming commands (velocity, PID tuning,
reset) and sends 5 auto-report data types at 50Hz each, interleaved 1ms apart to
avoid serial congestion.

### System Monitoring (`task_monitoring.c`)
Runs at 1Hz. Reads battery voltage, manages 3-level response (normal / low warning /
critical lockout), toggles heartbeat LED, and feeds the hardware watchdog only if
all other tasks are still alive.

### Safety Features

| Feature | What It Does |
|---------|-------------|
| Battery lockout | Motors refuse commands below 10.5V; auto-unlocks above 11.0V |
| Command timeout | Motors stop if no velocity command received for 2 seconds |
| Per-task watchdog | Watchdog only fed if all 4 tasks are running — MCU resets if any hangs |
| Velocity clamping | Commands capped at 1.0 m/s linear, 2.0 rad/s angular |
| Encoder anomaly rejection | Ignores readings above 3500 mm/s (EMI/noise protection) |

---

## 6. For ROS 2 Developers

### What you need to know

- The firmware is a **sealed unit**. You interact with it only through the
  `orbibot_hardware` ROS 2 package which handles all serial communication.
- Velocity commands arrive via `/cmd_vel` (standard `geometry_msgs/Twist`).
- Sensor data appears on standard ROS 2 topics (`/odom`, `/imu/data_raw`, etc.).
- PID gains are pre-tuned and saved to flash. You don't need to touch them
  unless you change motors or wheels.

### What you should NOT change

- **Do not modify firmware source files** unless you understand embedded C and FreeRTOS.
  A bad firmware change can brick the board (requires BOOT0 jumper recovery).
- **Do not change `orbibot_config.h` values** (wheel radius, encoder PPR, track width)
  unless the physical robot hardware changes. Wrong values = wrong odometry.
- **Do not enable debug output in production** (`ENABLE_DEBUG_OUTPUT=1`).
  Debug printf shares the serial line with the binary protocol and will corrupt data.

### What you CAN safely do from ROS 2

| Action | How |
|--------|-----|
| Drive the robot | Publish to `/cmd_vel` |
| Read odometry | Subscribe to `/odom` |
| Read IMU | Subscribe to `/imu/data_raw` or `/imu/data` |
| Check battery | Subscribe to `/orbibot/system_status` |
| Beep the buzzer | Publish to `/orbibot/beep` |
| Reset odometry | Call `/orbibot/reset_odometry` service |
| Tune PID (advanced) | Publish to `/orbibot/pid_params` |
| Save PID to flash | Publish to `/orbibot/pid_save` |

### How to extend safely

If you need to add new data from firmware to ROS 2:
1. Add a new report type in `protocol.c` (firmware side)
2. Add a new function code in `protocol.h`
3. Add parsing in `orbibot_hardware/rosmaster_driver.py` (ROS 2 side)
4. Publish to a new ROS 2 topic from `hardware_node.py`

> This requires re-flashing the firmware. See [Build & Upload](#build--upload) below.

---

## 7. Limitations and Design Decisions

### Current limitations

| Limitation | Reason |
|-----------|--------|
| 50Hz max sensor report rate | Serial bandwidth at 115200 baud (~22KB/s budget) |
| No camera/LiDAR on firmware | These are USB devices connected directly to RPi 5 |
| Single serial port | USART1 shared between protocol and debug — only one at a time |
| Accel bias calibrated at startup | X/Y offsets measured on boot; robot must be still and level when powered |
| OLED display is stub | Code compiles but no physical display on most OrbiBot builds |

### Key design decisions

| Decision | Why |
|----------|-----|
| Velocity-only odometry | Prevents wheel encoder position drift from accumulating in EKF |
| Single PID (not multi-level) | Indoor speeds (100-500 mm/s) don't need speed-dependent gains |
| 100Hz control loop | Sufficient for PID + odometry; leaves CPU headroom on 72MHz M3 |
| Midpoint (RK2) integration | Better accuracy than Euler during combined rotation + translation |
| Simple attitude estimate (not EKF) | Lightweight; the full EKF runs on the Raspberry Pi 5 instead |
| FreeRTOS (not bare-metal) | Clean task isolation; per-task watchdog; safe priority preemption |

---

## Build & Upload

```bash
cd src/orbibot_rosmaster_firmware

# Build
~/.platformio/penv/bin/pio run

# Upload (set BOOT0=HIGH on board, press RESET, then run)
~/.platformio/penv/bin/pio run --target upload

# After upload: set BOOT0=LOW, press RESET to run firmware
```

### Verify on robot

```bash
# Start the ROS 2 hardware node
ros2 launch orbibot_hardware hardware.launch.py

# Check data is flowing
ros2 topic hz /odom              # Should be ~50Hz
ros2 topic hz /imu/data_raw      # Should be ~50Hz
ros2 topic echo /odom --once     # Inspect odometry data

# Drive it from the web dashboard (orbibot_webgui); the gamepad package is switched off
```

---

## Debugging

### Quick checks from ROS 2

```bash
# Is serial port available?
ls -la /dev/motordriver

# Check topic rates
ros2 topic hz /odom
ros2 topic hz /imu/data_raw

# Check battery voltage
ros2 topic echo /orbibot/system_status --once

# Trigger a beep (200ms)
ros2 topic pub --once /orbibot/beep std_msgs/msg/UInt16 "data: 200"
```

### Common issues

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| No data on topics | Serial port not found | Check `/dev/motordriver` exists; verify USB cable |
| Motors don't move | Battery lockout | Check voltage > 10.5V on `/orbibot/system_status` |
| Motors stop after 2s | Command timeout | Ensure `/cmd_vel` is being published continuously |
| Odometry drifts badly | Wrong encoder direction | Re-flash firmware; run `test_encoder.py` |
| IMU reads zeros | SPI wiring fault | Re-flash firmware; run `test_imu.py` |

### Firmware test suite (direct serial, no ROS 2)

```bash
cd src/orbibot_rosmaster_firmware/tests
python3 run_all_tests.py --port /dev/motordriver
```

---

## Deep-Dive Documentation

These files contain low-level firmware details for embedded developers:

| Document | Audience | Contents |
|----------|----------|----------|
| [firmware-architecture.md](firmware-architecture.md) | Firmware devs | Layer design, task details, protocol packet formats |
| [rosmaster-board.md](../../docs/hardware/rosmaster-board.md) | Hardware/firmware devs | Pin mappings, timer configs, electrical specs |
| [test-report.md](test-report.md) | All | What has been tested on the hardware, and when |
| [CHANGELOG.md](CHANGELOG.md) | All | Version history and bug fix details |
| [known-issues.md](known-issues.md) | Firmware devs | Open issues, tech debt, improvement ideas |
| [tests/README.md](tests/README.md) | All | The serial test suite (no ROS 2 needed) |
| [orbibot_config.h](include/orbibot_config.h) | Firmware devs | All configurable parameters |

---

## Version

- **Version**: v2.0.0 (`include/firmware_version.h`). This is the firmware's own version, not an OrbiBot version.
- **Target**: STM32F103RCT6 (72MHz Cortex-M3)
- **Board**: Yahboom ROSMaster V3.0
- **Author**: Jewel Nath
