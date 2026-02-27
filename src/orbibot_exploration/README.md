# orbibot_exploration

Autonomous frontier-based exploration for OrbiBot. BFS frontier detection with Nav2 integration.

## Launch

```bash
# Requires SLAM and Navigation to be running
ros2 launch orbibot_exploration exploration.launch.py
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `auto_start` | `false` | Auto-start exploration on launch |
| `use_sim_time` | `false` | Use simulation time |

## Configuration

Parameters in `config/exploration_params.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `planner_frequency` | `0.5` | Frontier search frequency (Hz) |
| `progress_timeout` | `30.0` | Blacklist frontier after this many seconds |
| `min_frontier_size` | `0.5` | Minimum frontier size (meters) |
| `goal_tolerance` | `0.3` | Goal arrival tolerance (meters) |
| `potential_scale` | `3.0` | Distance weight (prefer closer) |
| `gain_scale` | `1.0` | Size weight (prefer larger) |
| `return_to_init` | `true` | Return to start when done |
| `robot_base_frame` | `base_footprint` | Robot TF frame |

## Topics

### Published
- `/orbibot/exploration/status` (String) — current state: idle, exploring, navigating, returning, complete, stopped
- `/orbibot/exploration/frontiers` (MarkerArray) — frontier visualization for RViz

### Subscribed
- `/map` (OccupancyGrid) — SLAM occupancy grid
- `/orbibot/exploration/command` (String) — control: `start`, `stop`, `pause`, `resume`

## Usage

```bash
# Start exploration
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: start"

# Pause
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: pause"

# Resume
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: resume"

# Stop
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: stop"
```

## Dependencies

- `rclpy` — ROS 2 Python client
- `nav2_msgs` — NavigateToPose action
- `tf2_ros` — Transform lookups
- `visualization_msgs` — RViz markers
