# orbibot_exploration

Frontier-based exploration for OrbiBot: it finds the edges between known and
unknown space on the SLAM map and sends Nav2 goals to them, until nothing is
left to explore.

**Status:** written, and not yet tested against a tuned Nav2. Stopping when
no reachable frontier is left is the part most likely to need work.

The frontier search is a Python re-implementation of the BFS search in
[m-explore-ros2](https://github.com/robo-friends/m-explore-ros2) (BSD).

## Launch

The simplest way is the bringup file, which also starts SLAM and Nav2. Start
the robot base first.

```bash
ros2 launch orbibot_bringup robot.launch.py         # terminal 1
ros2 launch orbibot_bringup exploration.launch.py   # terminal 2
```

`ros2 launch orbibot_exploration exploration.launch.py` starts only the
explorer, for when SLAM and Nav2 are already running. Its one argument is
`auto_start` (default `false`).

## Use

```bash
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: start"
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: pause"
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: resume"
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: stop"
```

## Topics

| Topic | Type | Direction | What it carries |
|---|---|---|---|
| `/map` | `OccupancyGrid` | in | The SLAM map |
| `/orbibot/exploration/command` | `String` | in | `start`, `stop`, `pause`, `resume` |
| `/orbibot/exploration/status` | `String` | out | `idle`, `exploring`, `navigating`, `returning`, `complete` or `stopped` |
| `/orbibot/exploration/frontiers` | `MarkerArray` | out | The frontiers, for RViz |

Goals go to Nav2's `NavigateToPose` action.

## Configuration

`config/exploration_params.yaml`:

| Parameter | Default | What it does |
|---|---|---|
| `planner_frequency` | `0.5` | How often to search for frontiers (Hz) |
| `progress_timeout` | `30.0` | Seconds without progress before a frontier is skipped |
| `min_frontier_size` | `0.5` | The smallest frontier worth visiting (m) |
| `goal_tolerance` | `0.3` | How close counts as arrived (m) |
| `potential_scale` | `3.0` | Weight for distance: prefer closer frontiers |
| `gain_scale` | `1.0` | Weight for size: prefer larger frontiers |
| `return_to_init` | `true` | Go back to the start when done |
| `robot_base_frame` | `base_footprint` | The robot's base frame |

## Dependencies

`rclpy`, `nav2_msgs`, `tf2_ros` and `visualization_msgs`.
