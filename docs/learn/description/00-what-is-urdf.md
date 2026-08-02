---
title: "00 - What is URDF?"
type: learn
area: description
package: orbibot_description
tags:
  - learn
  - description
---

# 00 - What is URDF?

**Why model robots digitally?**

---

## 🎯 Learning Objectives

- Understand why we need robot models
- Know what URDF is
- Understand the difference between URDF and Xacro

---

## 🤔 Why Model Robots?

### The Problem

```
You have a physical robot. But software needs to know:
- Where are the wheels?
- Where is the sensor?
- How big is the robot?
- How do parts move?
```

Without this information:
- Navigation can't plan paths
- Sensors data has no reference frame
- Visualization shows nothing
- Simulation is impossible

### The Solution: URDF

**URDF** = Unified Robot Description Format

A XML file that describes:
- Robot geometry (shapes, sizes)
- Joint connections (how parts move)
- Sensor positions
- Visual appearance

---

## 📝 What URDF Contains

```
Robot Model (URDF)
├── Links (rigid bodies)
│   ├── base_link (main body)
│   ├── wheel_front_left
│   ├── wheel_front_right
│   └── ...
│
├── Joints (connections)
│   ├── wheel_front_left_joint
│   ├── wheel_front_right_joint
│   └── ...
│
└── Materials (colors)
```

---

## 🔄 URDF vs Xacro

| URDF | Xacro |
|------|-------|
| Static XML | XML with macros |
| Verbose | Concise |
| Repetitive | Reusable |
| Hard to maintain | Easy to maintain |

### Example: URDF (without Xacro)

```xml
<robot name="robot">
  <!-- Wheel 1 -->
  <link name="wheel_fl">
    <visual>
      <geometry><cylinder radius="0.05" length="0.04"/></geometry>
    </visual>
  </link>
  
  <!-- Wheel 2 -->
  <link name="wheel_fr">
    <visual>
      <geometry><cylinder radius="0.05" length="0.04"/></geometry>
    </visual>
  </link>
  
  <!-- Repeat for 4 wheels... -->
</robot>
```

### Example: Xacro (with macros)

```xml
<robot name="robot" xmlns:xacro="http://www.ros.org/wiki/xacro">

  <!-- Define macro once -->
  <xacro:macro name="wheel" params="name">
    <link name="${name}">
      <visual>
        <geometry><cylinder radius="0.05" length="0.04"/></geometry>
      </visual>
    </link>
  </xacro:macro>

  <!-- Use macro 4 times -->
  <xacro:wheel name="wheel_fl"/>
  <xacro:wheel name="wheel_fr"/>
  <xacro:wheel name="wheel_bl"/>
  <xacro:wheel name="wheel_br"/>

</robot>
```

---

## 🎯 What You Can Do With URDF

1. **Visualize** - See robot in RViz
2. **Transform frames** - Know where sensors are
3. **Simulate** - Test in Gazebo (future)
4. **Navigate** - Path planning needs robot size

---

## 🎯 Key Takeaways

1. **URDF** = Robot description in XML
2. **Links** = Rigid body parts
3. **Joints** = Connections between links
4. **Xacro** = Macros to make URDF maintainable

---

## 📖 Next Steps

Learn URDF basics:

**→ Continue to:** [[01-urdf-basics]]

---

*Last Updated: March 2026*