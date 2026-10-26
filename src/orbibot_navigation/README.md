# orbibot_navigation

Nav2 configuration, launch file and saved maps for OrbiBot. It uses the MPPI
controller with the `Omni` motion model, because a mecanum robot can move
sideways.

**Status:** set up and run on the robot in a small room in March 2026;
nothing about it was measured. Its speed and acceleration limits were never
measured either. The footprint is the 350 × 250 mm frame, but the wheel
centres are 360 mm apart, so the wheels stick out of it.

## Launch

Start the robot base first (`ros2 launch orbibot_bringup robot.launch.py`),
then:

```bash
# Navigate on the default map, maps/map.yaml
ros2 launch orbibot_navigation navigation.launch.py

# Navigate on a map you saved
ros2 launch orbibot_navigation navigation.launch.py map_file:=$HOME/maps/my_map.yaml
```

| Argument | Default | What it does |
|---|---|---|
| `params_file` | `config/nav2_params.yaml` | Nav2 parameters |
| `map_file` | `maps/map.yaml` | The map to localise on |
| `autostart` | `true` | Starts the Nav2 lifecycle nodes |
| `use_composition` | `False` | Runs the nodes in one container |
| `use_respawn` | `False` | Restarts nodes that crash |

## Configuration

| File | For |
|---|---|
| `config/nav2_params.yaml` | Navigating on a saved map, with AMCL |
| `config/nav2_params_slam.yaml` | Navigating while slam_toolbox builds the map |
| `config/dock_database.yaml` | A minimal entry, so that Nav2's docking server starts |
| `maps/` | Two saved maps, `map` and `home_map`, at 0.05 m per cell |

The main settings in `nav2_params.yaml`:

- **Controller:** MPPI, `Omni` motion model, 5 Hz; 0.5 m/s forward and
  sideways, 1.5 rad/s turning.
- **Localisation:** AMCL with the omnidirectional motion model.
- **Planner:** NavFn.
- **Velocity chain:** controller (`cmd_vel_nav`) → `velocity_smoother` →
  `collision_monitor` → `/cmd_vel`.
- **Costmaps:** a rolling local costmap and a global costmap with the static
  map, both with a 0.25 m inflation radius and the robot's 350 × 250 mm
  footprint.
- **Frames:** `map`, `odom`, and `base_footprint` as the robot's base frame.

`nav2_params_slam.yaml` runs MPPI at 8 Hz with a longer horizon.

## Dependencies

`nav2_bringup`, `nav2_controller` (MPPI), `nav2_amcl` and `nav2_map_server`.
