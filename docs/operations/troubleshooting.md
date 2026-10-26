# Troubleshooting

The first checks when something doesn't work, from the serial link up. Each
package's `known-issues.md` lists the problems that are already known.

## Is the motor board talking?

```bash
ls -l /dev/motordriver /dev/lidar         # the udev names exist
groups | grep dialout                      # you can open serial ports
ros2 topic hz /imu/data_raw                # about 50 Hz with robot.launch.py running
ros2 service call /orbibot/get_firmware_version orbibot_msgs/srv/GetFirmwareVersion "{}"
```

| Symptom | Likely cause | Fix |
|---|---|---|
| `/dev/motordriver` missing | udev rules not installed, or a different USB serial chip | Run `src/orbibot_hardware/scripts/setup_permissions.sh`; check `lsusb` for `1a86:7523` |
| Permission denied on the port | Not in `dialout` | `sudo usermod -aG dialout $USER`, then log out and in |
| Works for a minute, then reconnects in a loop | USB cable, power or an STM32 reset | Try another cable and port; check the battery; make sure no other process holds the port |
| A topic is silent but others work | The firmware and the driver disagree about a packet's length, and the driver drops it | Rebuild and flash the firmware from this commit; compare `include/protocol.h` with `rosmaster_driver.py` |
| The motors don't move | Motors off, battery below cut-off, or no `/cmd_vel` | `ros2 topic echo /orbibot/system_status --once`; `ros2 topic echo /cmd_vel` |

Without ROS at all, the firmware's own test suite talks to the board
directly (wheels off the ground):

```bash
cd src/orbibot_rosmaster_firmware/tests
python3 run_all_tests.py --port /dev/motordriver
```

## Is the LiDAR running?

```bash
ros2 topic hz /scan
ros2 topic echo /scan --once | head
```

`robot.launch.py` starts the LiDAR 5 s after everything else, as a separate
process. If `/scan` never appears, check `/dev/lidar` and that nothing else
opened it.

## Are the frames right?

```bash
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 run tf2_tools view_frames
```

The chain is `map → odom → base_footprint → base_link → sensors`. Exactly one
node may publish `map → odom` (slam_toolbox or AMCL) and one `odom →
base_footprint` (the EKF). Two publishers on one edge make the robot jump in
RViz.

## The web dashboard

| Symptom | Fix |
|---|---|
| "Failed to connect to rosbridge" | Start `ros2 launch orbibot_webgui webgui.launch.py`; check port 9090 |
| Panels are empty | Is `robot.launch.py` running? |
| The camera is black | Start with `use_video:=true` and `use_camera:=true` on the base; check `ros2 topic hz /camera/color/image_raw` |
| The chat panel is offline | Start `ros2 launch orbibot_agent chat_server.launch.py` |

## More

- [The testing guide](../testing/README.md) has a troubleshooting table for
  each stage.
- [The debugging lesson](../learn/hardware/10-debugging-guide.md) walks through
  the serial bridge in detail.
- `ros2 topic list`, `ros2 node list` and `ros2 doctor` are the general ROS 2
  checks; [the CLI lesson](../learn/ros2/12-cli-tools.md) covers them.
