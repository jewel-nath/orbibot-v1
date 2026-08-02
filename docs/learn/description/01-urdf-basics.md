---
title: "01 - URDF Basics"
type: learn
area: description
package: orbibot_description
tags:
  - learn
  - description
---

# 01 - URDF Basics

**Links, joints, and geometry**

---

## 🎯 Learning Objectives

- Understand links and joints
- Create basic URDF elements
- Know joint types

---

## 🔗 Links

A **link** is a rigid body with visual and collision properties.

```xml
<link name="base_link">
  <!-- Visual appearance -->
  <visual>
    <geometry>
      <box size="0.5 0.3 0.1"/>
    </geometry>
    <material name="blue"/>
  </visual>
  
  <!-- Collision shape -->
  <collision>
    <geometry>
      <box size="0.5 0.3 0.1"/>
    </geometry>
  </collision>
</link>
```

### Geometry Types

| Type | Use For |
|------|---------|
| `<box size="x y z"/>` | Rectangular bodies |
| `<cylinder radius="r" length="l"/>` | Wheels, rods |
| `<sphere radius="r"/>` | Balls, joints |
| `<mesh filename="file.stl"/>` | Complex shapes |

---

## 🔧 Joints

A **joint** connects two links and defines how they move.

```xml
<joint name="wheel_joint" type="continuous">
  <parent link="base_link"/>
  <child link="wheel_link"/>
  <origin xyz="0.2 0.15 0" rpy="0 0 0"/>
  <axis xyz="0 1 0"/>
</joint>
```

### Joint Types

| Type | Movement | Example |
|------|----------|---------|
| `fixed` | No movement | Sensor mounts |
| `continuous` | Rotates freely | Wheels |
| `revolute` | Rotates with limits | Arms |
| `prismatic` | Slides | Linear actuators |

---

## 📍 Origin and Axis

```
origin xyz="x y z" rpy="roll pitch yaw"

xyz = position (meters)
rpy = rotation (radians)
```

---

## 🎯 Key Takeaways

1. **Link** = Rigid body with shape
2. **Joint** = Connection with movement type
3. **Origin** = Where child attaches to parent
4. **Axis** = Direction of rotation/translation

---

## 📖 Next Steps

Learn Xacro macros:

**→ Continue to:** [[02-xacro-macros]]

---

*Last Updated: March 2026*