---
title: "Part 5: Mecanum Wheel Theory"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "30 minutes"
tags:
  - learn
  - firmware
---

# Part 5: Mecanum Wheel Theory

**Duration**: 30 minutes  
**Prerequisites**: none — the vectors and frame conventions you need are
introduced inline. For the ROS 2 side of frames, see [[09-tf2-transforms]].

---

## Learning Objectives

After this lesson, you will understand:
- How mecanum wheels work mechanically
- Why they enable omnidirectional movement
- The ABBA wheel arrangement
- Force vectors and roller angles

---

## What Are Mecanum Wheels?

Mecanum wheels are special wheels that allow a robot to move in **any direction** without turning.

### Regular Wheel Limitations

```
Regular Wheel:
- Can only roll forward/backward
- To move sideways, robot must turn
- Limited to differential drive

Mecanum Wheel:
- Can roll forward/backward
- Rollers allow sideways force
- Can strafe (move sideways)!
```

---

## Wheel Construction

A mecanum wheel has two key parts:

```
┌─────────────────────────┐
│    Mecanum Wheel        │
│                         │
│  ╱╲   ╱╲   ╱╲   ╱╲     │
│ ╱  ╲ ╱  ╲ ╱  ╲ ╱  ╲    │ ← Rollers at 45°
│╱    ╳    ╳    ╳    ╲   │   (angled)
│      ╲    ╲    ╲        │
│       ╲    ╲    ╲       │
│        Hub (center)      │
└─────────────────────────┘
```

### Components

1. **Hub**: The main wheel structure, attached to motor
2. **Rollers**: Small cylinders around the rim, angled at 45 degrees
3. **Bearings**: Allow rollers to spin freely

---

## How Rollers Enable Sideways Motion

### Forward Motion (All Wheels Forward)

```
Forces when all wheels turn forward:
        Front
    ╱╲       ╱╲
   ╱  ╲     ╱  ╲
  ╱    ╲   ╱    ╲
  │  ↑   │ │  ↑   │   All rollers push
  │  ↑   │ │  ↑   │   robot forward
  ╲    ╱   ╲    ╱
   ╲  ╱     ╲  ╱
    ╲╱       ╲╱
        Rear
    
Result: Robot moves forward
```

### Sideways Motion (Opposite Wheels)

```
Forces for sideways (strafe) movement:

        Front
    ╱╲       ╲╱
   ╱  ╲     ╱  ╲
  ╱    ╲   ╱    ╲
  │  ↗   │ │  ↖   │   Diagonal forces
  │  ↗   │ │  ↖   │   combine to push
  ╲    ╱   ╲    ╱    robot sideways
   ╲  ╱     ╲  ╱
    ╲╱       ╱╲
        Rear
    
Left wheels forward + Right wheels backward = Strafe right
```

### The Physics

Each roller is angled at 45 degrees. When the wheel rotates:
- **Main force**: Forward/backward (wheel rotation)
- **Secondary force**: Sideways (roller rotation)

By combining different wheel speeds, we can create movement in any direction!

---

## ABBA Wheel Arrangement

OrbiBot uses the standard ABBA layout:

```
        Front of Robot
        
    A       ╱╲       B
   ╱╲     ╱  ╲     ╱╲
  ╱  ╲   ╱    ╲   ╱  ╲
 │ FL │ │ FR │     FL = Front-Left (Type A)
  ╲  ╱   ╲    ╱   ╲  ╱    FR = Front-Right (Type B)
   ╲╱     ╲  ╱     ╲╱
           ╲╱
           
    B       ╱╲       A
   ╱╲     ╱  ╲     ╱╲
  ╱  ╲   ╱    ╲   ╱  ╲
 │ BL │ │ BR │     BL = Back-Left (Type B)
  ╲  ╱   ╲    ╱   ╲  ╱    BR = Back-Right (Type A)
   ╲╱     ╲  ╱     ╲╱
           ╲╱
           
        Rear of Robot
```

### Type A vs Type B

| Type | Roller Angle | Position |
|------|--------------|----------|
| Type A | +45 degrees (top-left to bottom-right) | Front-Left, Back-Right |
| Type B | -45 degrees (top-right to bottom-left) | Front-Right, Back-Left |

This arrangement is **critical** - swapping A and B wheels prevents proper movement!

---

## Movement Patterns

### Forward/Backward

```
All wheels turn same direction:
  FL: Forward  FR: Forward
  BL: Forward  BR: Forward
  
Result: Pure forward motion
```

### Rotation (Turning in place)

```
Opposite sides turn opposite ways:
  FL: Forward   FR: Backward
  BL: Forward   BR: Backward
  
Result: Robot spins around center
```

### Strafe Left/Right

```
Diagonal wheels turn opposite:
  FL: Forward   FR: Backward
  BL: Backward  BR: Forward
  
Result: Pure sideways motion!
```

### Diagonal Movement

```
Various combinations create diagonal motion:
  FL: Forward   FR: Stop
  BL: Stop      BR: Forward
  
Result: Diagonal forward-right
```

---

## Force Vector Analysis

Each wheel contributes a force vector at 45 degrees:

```
Type A Wheel Force (+45°):
     ╱↑
    ╱ │
   ╱  │ Force vector
  ╱   │ at 45°
 ─────┘

Type B Wheel Force (-45°):
 ─────┐
  ╲   │ Force vector
   ╲  │ at -45°
    ╲ │
     ╲↓
```

When you add these vectors mathematically, you can achieve any net force direction!

---

## OrbiBot Wheel Specifications

| Parameter | Value |
|-----------|-------|
| Wheel Diameter | 100 mm (50 mm radius) |
| Roller Angle | 45 degrees |
| Number of Rollers | 8-12 per wheel |
| Wheel Type | ABBA arrangement |
| Motor Gear Ratio | 30:1 |
| Encoder Resolution | 1320 counts/revolution |

---

## Common Mistakes

### Mistake 1: Wrong Wheel Arrangement

```
WRONG (AAAA):
All wheels same type → Cannot strafe properly!

CORRECT (ABBA):
Alternating types → Full omnidirectional motion
```

### Mistake 2: Swapped A and B Wheels

```
If you swap FL and FR:
- Forward still works
- Strafe moves in wrong direction!
- Rotation may be reversed
```

### Mistake 3: Incorrect Motor Directions

```
If one motor wired backwards:
- Robot moves in curves
- Cannot drive straight
- Check encoder directions!
```

---

## Exercise: Predict Movement

Given these wheel directions, what happens?

```
Case 1:
  FL: Forward   FR: Forward
  BL: Forward   BR: Forward
  Answer: ?

Case 2:
  FL: Forward   FR: Backward
  BL: Backward  BR: Forward
  Answer: ?

Case 3:
  FL: Stop      FR: Forward
  BL: Forward   BR: Stop
  Answer: ?
```

**Answers**:

<details>
<summary>Click for answers</summary>

**Case 1**: All forward → Robot moves **forward**

**Case 2**: Diagonal opposites → Robot **strafes right**

**Case 3**: FL stop, FR forward, BL forward, BR stop → Robot moves **diagonal forward-left**

</details>

---

## Summary

- **Mecanum wheels** have angled rollers that enable sideways force
- **ABBA arrangement** is required for proper omnidirectional movement
- **Different wheel speed combinations** create different movements:
  - All same = forward/backward
  - Opposite sides = rotation
  - Diagonal opposites = strafe

---

## Next Lesson

[[51-inverse-kinematics]] - Calculate wheel speeds from robot velocity

---

*OrbiBot Firmware Study Guide*  
*Part 5 of 10*