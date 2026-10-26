# Getting started

How to set up OrbiBot V1's software from scratch: a Raspberry Pi 5 with
Ubuntu 24.04 and ROS 2 Jazzy, the STM32 firmware, and a first launch. The
steps are the ones V1 was set up with; check the version notes at the end.

## What you need

- The robot: the welded mecanum base with the Yahboom ROSMaster V3.0 board,
  the RPLIDAR A1 and, optionally, the RealSense D435 ([hardware](hardware/README.md))
- A Raspberry Pi 5 with **Ubuntu 24.04** (64-bit) and **ROS 2 Jazzy**
  installed ([the ROS 2 install guide](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html))
- A charged 4S LiFePO4 battery, above 11.0 V
- Blocks or a stool to lift the wheels off the ground for the first tests

Read [the safety rules](../.claude/rules/robot-safety.md) before you command
any motion: the wheels are real.

## 1. Get the code

The repository root is the colcon workspace. Several docs and the agent's
`.env.local` lookup assume `~/orbibot_ws`:

```bash
git clone https://github.com/jewel-nath/orbibot-v1.git ~/orbibot_ws
cd ~/orbibot_ws
```

## 2. Give the devices fixed names

```bash
./src/orbibot_hardware/scripts/setup_permissions.sh
```

Run it as your normal user; it uses `sudo` where it needs to. It writes
`/etc/udev/rules.d/99-orbibot.rules`, so the motor board (CH340, `1a86:7523`)
appears as `/dev/motordriver` and the LiDAR (CP2102, `10c4:ea60`) as
`/dev/lidar`, gives the RealSense IDs access, and adds you to the `dialout`,
`plugdev` and `video` groups. Log out and back in afterwards. Ignore its
"ROSMaster_Lib not found" message: the driver is now part of
`orbibot_hardware`.

```bash
ls -l /dev/motordriver /dev/lidar   # both should exist
```

## 3. Install the dependencies and build

```bash
source /opt/ros/jazzy/setup.bash
sudo rosdep init   # once per machine; skip if already done
rosdep update
rosdep install --from-paths src --ignore-src -y
colcon build --symlink-install
source install/setup.bash
```

`rosdep` pulls in slam_toolbox, Nav2, robot_localization,
imu_filter_madgwick, the RPLIDAR and RealSense drivers, rosbridge and the
Python packages it can resolve. Install with pip what it can't, for example
`google-genai` for the agent's default Gemini provider. The firmware is
skipped by colcon (it carries a `COLCON_IGNORE`).

## 4. Build and flash the firmware

The firmware is a PlatformIO project. Its toolchain is pinned in
`platformio.ini` so the Pi can build it.

```bash
# once: PlatformIO's own installer (Ubuntu 24.04 won't pip-install it system-wide)
curl -fsSL -o get-platformio.py https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py
python3 get-platformio.py
cd src/orbibot_rosmaster_firmware
~/.platformio/penv/bin/pio run    # always build first
```

The board has no automatic bootloader circuit, so flashing needs two hands:

1. Set the BOOT0 jumper HIGH (3.3 V) and press RESET.
2. Upload: `~/.platformio/penv/bin/pio run --target upload`
3. Set BOOT0 LOW (GND) and press RESET again.

Check it with the serial test suite, **with the wheels off the ground**:

```bash
cd tests && python3 run_all_tests.py --port /dev/motordriver
```

## 5. First launch

With the wheels still in the air:

```bash
ros2 launch orbibot_bringup robot.launch.py
```

In another terminal:

```bash
ros2 topic hz /imu/data_raw      # about 50 Hz
ros2 topic hz /joint_states      # about 50 Hz
ros2 topic echo /orbibot/system_status --once   # battery voltage, motors enabled
ros2 run tf2_ros tf2_echo odom base_footprint
```

`robot.launch.py` turns the motors on 6 s after it starts. A short, slow test:

```bash
ros2 topic pub --rate 10 --times 20 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
```

All four wheels should turn forwards and stop about 2 s after the last
command. Next: [running the robot](operations/running.md).

## Version notes

V1 was set up in 2025 and 2026 on Ubuntu 24.04 and ROS 2 Jazzy. Package
versions move on: if `rosdep` or a launch file fails, check the package's
`known-issues.md` and the ROS 2 release notes first.
