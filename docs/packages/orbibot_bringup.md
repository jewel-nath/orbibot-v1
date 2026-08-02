---
title: "orbibot_bringup"
type: package
tags:
  - package
  - bringup
---

# orbibot_bringup

Where cross-package composition lives. Every other package launches only its
own nodes; this one assembles them.

> **The API reference is `src/orbibot_bringup/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

```bash
ros2 launch orbibot_bringup robot.launch.py        # description + hardware + LiDAR + EKF
ros2 launch orbibot_bringup mapping.launch.py      # + slam_toolbox
ros2 launch orbibot_bringup exploration.launch.py  # + Nav2 + frontier explorer
```

Layered: each builds on the one above it.

## The rule

If a launch file needs nodes from two packages, it belongs here. This is what
keeps `orbibot_slam` from quietly starting a hardware node and leaving two of
them fighting over the serial port.

## Related

[[packages-moc]] · [[system-overview]] · [[orbibot_navigation]] · [[orbibot_slam]]
