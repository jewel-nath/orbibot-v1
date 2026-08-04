# /robot-start — bring the robot stack up

Starts the base: description, command arbitration, hardware bridge, LiDAR, EKF.
**Motors are not armed by this.** Launching is safe with the robot on the floor.

## Before you launch

```bash
.claude/scripts/stop.sh --check
```

If anything is already running, stop it first — a second stack cannot open
`/dev/motordriver` or `/dev/lidar`, and the failure looks like a hardware fault.
This has already cost a wasted trip to the robot once; see the diagnostic-trap
section in `src/orbibot_sensors/sensors-issue.md`.

## Launch

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch orbibot_bringup robot.launch.py
```

Options:

| Argument | Default | Use |
|---|---|---|
| `use_camera:=true` | false | start the RealSense too |
| `motors_enabled:=true` | **false** | arm motors 6 s after start — **only with the robot elevated or the floor clear** |
| `lidar_port:=/dev/…` | `/dev/lidar` | override the LiDAR device |
| `motor_port:=/dev/…` | `/dev/motordriver` | override the board device |

Other entry points:

```bash
ros2 launch orbibot_bringup mapping.launch.py       # + slam_toolbox
ros2 launch orbibot_bringup exploration.launch.py   # + frontier explorer
ros2 launch orbibot_webgui webgui.launch.py         # rosbridge :9090, WebRTC :8081
```

## Confirm it actually came up

Give it ~20 s — the LiDAR starts on a 5 s delay and takes a few seconds to spin
up. Then check the numbers, not the absence of errors:

```bash
ros2 topic info /cmd_vel     # Publisher count MUST be 1 (twist_mux)
for t in /scan /odometry/filtered /imu/data_raw /joint_states; do
  echo -n "$t: "
  timeout 12 ros2 topic hz $t --window 40 2>&1 \
    | grep -oE 'average rate: [0-9.]+' | tail -1
done
```

Expected: `/scan` 8.0, the rest 50.0. Full table in `/robot-status`.

## If the LiDAR times out

`RESULT_OPERATION_TIMEOUT` or `cannot retrieve rplidar health code` usually is
**not** a dead device. Check these two first:

```bash
ros2 param get /rplidar_node serial_port     # must be /dev/lidar
pgrep -cf '^/opt/ros/jazzy/lib/rplidar_ros/rplidar_composition'   # must be 1
```

Both failure modes have happened here — the node handed the wrong device
(BRINGUP-2), and twelve copies of the node fighting over the port. A genuinely
wedged A1 still answers S/N and firmware version and fails only at the health
check; if even those fail, suspect power or cabling.

## Stopping

Ctrl+C in that terminal stops everything in ~1.1 s. From another terminal, or
from a script or an agent session with no terminal, use `/robot-stop`.

## Related

`/robot-status` · `/robot-stop` · `/robot-drive` · `src/orbibot_bringup/README.md`
