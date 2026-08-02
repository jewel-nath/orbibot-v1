---
title: "orbibot_navigation"
type: package
tags:
  - package
  - navigation
---

# orbibot_navigation

Nav2 parameters, launch, and saved maps. MPPI with the `Omni` motion model,
because the robot strafes.

> **The API reference is `src/orbibot_navigation/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

```bash
ros2 launch orbibot_navigation navigation.launch.py map:=$HOME/maps/my_map.yaml
```

| Config | For |
|---|---|
| `nav2_params.yaml` | Against a saved map (AMCL) |
| `nav2_params_slam.yaml` | Against live SLAM |
| `dock_database.yaml` | Minimal — present so the docking server does not crash Nav2 |
| `maps/` | `home_map`, `map` |

Velocity chain: controller → `velocity_smoother` → `collision_monitor` →
`/cmd_vel`.

## Open

**Every limit in here was tuned on a Pi 4 and has never been re-measured.**
Footprint 350 × 250 mm, inflation 0.55 m, and the velocity/acceleration caps
all need re-deriving from Phase 1's measured maxima before they mean anything —
roadmap Phase 6.

## Related

[[packages-moc]] · [[orbibot_slam]] · [[orbibot_exploration]] ·
[[command-pipeline]]
