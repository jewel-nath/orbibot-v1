---
title: "orbibot_description"
type: package
tags:
  - package
  - description
---

# orbibot_description

The robot's URDF/Xacro model, meshes, and RViz configs. Source of the
`base_footprint → base_link → sensor_links` part of the TF chain.

> **The API reference is `src/orbibot_description/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

```bash
ros2 launch orbibot_description description.launch.py
ros2 launch orbibot_description rviz.launch.py
```

`urdf/orbibot.urdf.xacro` is the single model.

## The convention

**The base frame is `base_footprint`, never `base_link`.** Every config in
every package follows this. `base_link` exists, but it hangs below
`base_footprint`, not the other way round.

Physical: wheelbase × track 260 × 360 mm, footprint 350 × 250 mm, wheel radius
50 mm, ~6 kg.

## Related

[[packages-moc]] · [[system-overview]] · [[description-moc]] · [[components]]
