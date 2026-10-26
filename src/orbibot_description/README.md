# orbibot_description

OrbiBot's robot model: one Xacro file, three meshes and two RViz setups. It
gives the `base_footprint → base_link → sensor` part of the TF tree.

**Status:** used on the robot, through `robot.launch.py`.

## Launch

```bash
ros2 launch orbibot_description description.launch.py   # robot_state_publisher (robot.launch.py runs this)
ros2 launch orbibot_description description.launch.py use_jsp:=true   # with joint_state_publisher, without the robot
ros2 launch orbibot_description rviz.launch.py          # RViz with rviz/orbibot.rviz
```

## Files

| Path | What it is |
|---|---|
| `urdf/orbibot.urdf.xacro` | The whole model: base, wheels, LiDAR, camera, IMU |
| `meshes/mechanical-wheel-FrontLeft-BackRight.stl` | Mecanum wheel mesh, used front-left and back-right |
| `meshes/mechanical-wheel-FrontRight-BackLeft.stl` | Mecanum wheel mesh, used front-right and back-left |
| `meshes/RPLidar-A1.stl` | The RPLIDAR A1 housing |
| `rviz/orbibot.rviz`, `rviz/description.rviz` | RViz setups |

The model also keeps the Gazebo plugin and sensor blocks from an earlier
simulation package. V1 has no simulation, and nothing uses them.

## Dimensions

| | |
|---|---|
| Wheel radius | 50 mm (100 mm mecanum wheels) |
| Wheelbase × track | 260 × 360 mm (front to back × left to right, wheel centres) |
| Base box | 350 × 250 × 100 mm |
| Mass | 6.0 kg (a model value, not a weighing) |

## Frames

```
base_footprint                 on the floor, under the robot's centre
└── base_link                  50 mm up, at the wheel axles
    ├── wheel_front_left_link   ┐
    ├── wheel_back_left_link    │ continuous joints,
    ├── wheel_front_right_link  │ in the M1 to M4 order of the motor board
    ├── wheel_back_right_link   ┘
    ├── lidar_link             180 mm above base_link
    ├── imu_link               20 mm above base_link
    └── camera_link            at the front edge, 20 mm above base_link
        ├── camera_color_frame → camera_color_optical_frame
        └── camera_depth_frame → camera_depth_optical_frame
```

**The base frame is `base_footprint`, never `base_link`.** Every config in
the workspace uses it. The full chain on the robot is
`map → odom → base_footprint → base_link → sensors`: slam_toolbox or AMCL
publish `map → odom`, and the EKF publishes `odom → base_footprint`.

The right-hand wheels use a flipped frame, so their joint axis is `0 0 -1`.
Front-left and back-right share one wheel mesh, and front-right and back-left
the other, because a mecanum set has two mirrored roller directions.

## Checking it

```bash
ros2 run tf2_ros tf2_echo odom base_footprint   # one transform
ros2 run tf2_tools view_frames                  # the whole tree, as a PDF
ros2 topic echo /joint_states --once            # the wheel joints
```

| Problem | Likely cause |
|---|---|
| The robot floats or sinks in RViz | RViz's fixed frame is `base_link`; use `odom` or `map` |
| Wheels don't turn in RViz | `/joint_states` is missing: is `hardware_node` running? |
| The camera image is rotated | Use `camera_color_optical_frame` for images |

## Meshes

Where the three STL meshes came from is not recorded: the wheel files were
exported from CAD Exchanger, and the LiDAR file from Blender. If you know
their source, please open an issue so it can be credited.
