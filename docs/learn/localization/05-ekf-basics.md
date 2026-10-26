# 05 - EKF Basics

**Extended Kalman Filter for state estimation**

---

## 🎯 Learning Objectives

- Understand Kalman filter concept
- Know prediction and update steps
- Understand covariance

---

## 🤔 What is a Kalman Filter?

**Kalman Filter** = Optimal state estimator for linear systems.

```
State: [x, y, yaw, vx, vy, vyaw]  (position, orientation, velocities)

Prediction: Where should I be? (from model)
Update: Where am I really? (from sensors)
```

---

## 🔄 Two Steps

### 1. Prediction (from model)

```
x_pred = x_prev + vx * dt
y_pred = y_prev + vy * dt
yaw_pred = yaw_prev + vyaw * dt
```

### 2. Update (from sensors)

```
K = uncertainty_pred / (uncertainty_pred + uncertainty_sensor)
x = x_pred + K * (measurement - x_pred)
```

---

## 📊 Covariance Matrix

```
Uncertainty representation:

P = [ σ_x²    0      0   ]
    [  0    σ_y²     0   ]
    [  0     0    σ_yaw² ]

Smaller = more confident
Larger = less confident
```

---

## 🎯 Key Takeaways

1. **Prediction** = Model-based estimate
2. **Update** = Sensor correction
3. **Kalman Gain (K)** = How much to trust sensor
4. **Covariance** = Uncertainty

---

## 📖 Next Steps

Learn EKF configuration:

**→ Continue to:** [06 - EKF Configuration](06-ekf-configuration.md)

---

*Last Updated: March 2026*