---
title: "OrbiBot Description Study Guide"
type: learn
area: description
package: orbibot_description
tags:
  - learn
  - description
---

# OrbiBot Description Study Guide

**Robot modeling with URDF and Xacro**

---

## Prerequisites

**REQUIRED:**
1. **[ROS2 Study Guide](../ros2/)** - Common ROS2 fundamentals
   - Minimum: 00-ros2-overview, 03-topics-pub-sub, 09-tf2-transforms, 11-rviz-basics
   - Essential: Nodes, TF2, RViz

2. **Basic XML** - Understanding tags and attributes
3. **3D coordinates** - X, Y, Z axes and rotations

---

## What You'll Learn

By completing this guide, you will understand:

- **URDF** - Robot description format
- **Xacro** - Macros for reusable robot parts
- **Coordinate frames** - How TF2 transforms work
- **Joint types** - How robot parts connect
- **Visualization** - See robot in RViz

---

## Study Files

| File | Topic | Time |
|------|-------|------|
| [[00-what-is-urdf]] | Why model robots? | 10 min |
| [[01-urdf-basics]] | Links and joints | 20 min |
| [[02-xacro-macros]] | Reusable components | 25 min |
| [[03-orbibot-urdf-walkthrough]] | Complete OrbiBot model | 30 min |
| [[04-tf-tree]] | Coordinate frames | 20 min |
| [[05-visualization]] | RViz and debugging | 15 min |

---

## Learning Path

### Week 1: URDF Fundamentals
- 00-what-is-urdf.md
- 01-urdf-basics.md
- 02-xacro-macros.md

### Week 2: OrbiBot Specific
- 03-orbibot-urdf-walkthrough.md
- 04-tf-tree.md
- 05-visualization.md

---

## Related Files

```
src/orbibot_description/
├── urdf/
│   └── orbibot.urdf.xacro      ← Main robot model
├── meshes/
│   └── *.stl                   ← 3D visual meshes
├── launch/
│   ├── description.launch.py   ← Publish robot description
│   └── rviz.launch.py          ← Visualize robot
└── rviz/
    └── orbibot.rviz            ← RViz configuration
```

---

## Start Here

**Begin with:** [[00-what-is-urdf]]

---

**Happy Learning!**