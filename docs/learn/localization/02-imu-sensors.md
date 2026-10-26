# 02 - IMU Sensors

> **Note:** this lesson was written before 2026-04-28, when OrbiBot stopped using the ICM-20948's magnetometer. It explains the magnetometer because it is part of the chip; OrbiBot found it unusable indoors, next to a steel frame, motors and battery currents. Today the IMU sends gyro and accelerometer only, in a 12-byte packet, and the yaw comes from the gyro alone.

**Inertial Measurement Unit**

---

## 🎯 Learning Objectives

- Understand IMU components
- Know what each sensor measures
- Understand coordinate frames

---

## 📊 IMU Components

| Sensor | Measures | Unit |
|--------|----------|------|
| **Accelerometer** | Linear acceleration | m/s² |
| **Gyroscope** | Angular velocity | rad/s |
| **Magnetometer** | Magnetic field | μT |

---

## 📐 What They Measure

### Accelerometer

```
Measures: Force per unit mass (including gravity)

When stationary:
  z-axis = 9.8 m/s² (gravity)
  x, y = 0

When moving:
  z-axis = 9.8 + acceleration
```

### Gyroscope

```
Measures: Rotation rate around 3 axes

roll_rate  = rotation around x-axis
pitch_rate = rotation around y-axis
yaw_rate   = rotation around z-axis
```

### Magnetometer

```
Measures: Earth's magnetic field

Points to magnetic north
Used to get absolute heading (yaw)
```

---

## 📨 IMU Message

```python
from sensor_msgs.msg import Imu

imu = Imu()
imu.header.frame_id = 'imu_link'

# Orientation (from sensor fusion)
imu.orientation.x = 0.0
imu.orientation.y = 0.0
imu.orientation.z = 0.0
imu.orientation.w = 1.0  # Quaternion

# Angular velocity (gyro)
imu.angular_velocity.x = 0.0  # rad/s
imu.angular_velocity.y = 0.0
imu.angular_velocity.z = 0.5  # turning left

# Linear acceleration (accel)
imu.linear_acceleration.x = 0.1  # m/s²
imu.linear_acceleration.y = 0.0
imu.linear_acceleration.z = 9.8  # gravity
```

---

## 🎯 Key Takeaways

1. **Accelerometer** = Linear acceleration + gravity
2. **Gyroscope** = Rotation rate
3. **Magnetometer** = Absolute heading, where the field is clean (OrbiBot does not use one)
4. **Combined** = Complete orientation

---

## 📖 Next Steps

Learn sensor fusion:

**→ Continue to:** [03 - Sensor Fusion Concept](03-sensor-fusion-concept.md)

---

*Last Updated: March 2026*