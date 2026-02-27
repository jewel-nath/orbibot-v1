# orbibot_navigation

Nav2 navigation stack for OrbiBot mecanum robot. MPPI controller with Omni motion model.

## Launch

```bash
ros2 launch orbibot_navigation navigation.launch.py

# With custom map
ros2 launch orbibot_navigation navigation.launch.py map_file:=/path/to/map.yaml
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `params_file` | `config/nav2_params.yaml` | Nav2 parameters file |
| `map_file` | `maps/map.yaml` | Map file for localization |
| `use_sim_time` | `false` | Use simulation time |
| `autostart` | `true` | Auto-start Nav2 stack |
| `use_composition` | `false` | Use composed nodes |
| `use_respawn` | `false` | Respawn crashed nodes |

## Configuration

Key components in `config/nav2_params.yaml`:

- **MPPI Controller** — Omni motion model for mecanum wheels; full vy range (`vy_min: -0.5`)
- **AMCL** — OmniMotionModel; adaptive recovery alphas enabled (fast: 0.1, slow: 0.001); `laser_min_range: 0.15`
- **NavFn Planner** — A* global path planning
- **Velocity Smoother** — controller (`cmd_vel_nav`) → smoother → collision_monitor (`cmd_vel`) chain
- **Collision Monitor** — `FootprintApproach` (velocity-adaptive slowdown) + `PolygonStop` (hard stop for very close obstacles)
- **Costmaps** — Local (rolling 6×6m) and global; update frequency matches controller frequency (10Hz)

## Frame Configuration

- **robot_base_frame**: `base_footprint`
- **global_frame**: `map`
- **odom_frame**: `odom`
- **scan_topic**: `/scan`

## Robot Specifications

- Footprint: 350mm × 250mm mecanum
- Max velocity: 0.5 m/s (x, y), 1.5 rad/s (angular — aligned across MPPI, smoother, and behavior server)
- Inflation radius: 0.55m (costmap safety buffer)
- Controller frequency: 10Hz (RPi 5 appropriate)

## Dependencies

- `nav2_bringup` — Nav2 launch infrastructure
- `nav2_controller` — MPPI controller
- `nav2_amcl` — Localization
- `nav2_map_server` — Map serving
