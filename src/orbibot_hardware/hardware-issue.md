# Hardware Node Issue Tracker

**Package:** `orbibot_hardware` (ROS 2 serial bridge, Python)
**Last Updated:** 2026-03-25

---

## 🔴 Open

### HW-BUG-1: EKF Output Rate ~2.5 Hz Instead of Configured 25 Hz
**Opened:** 2026-03-25
**Severity:** MEDIUM
**Affects:** `orbibot_localization` (robot_localization EKF), navigation performance

**Symptom:** `/odometry/filtered` publishes at ~2.5 Hz regardless of robot state
(stationary or moving). The EKF `frequency` parameter is set to 25.0 Hz in
`ekf_params.yaml`, but actual output rate is 10× lower. The `/tf` (odom→base_footprint)
broadcast rate matches at ~2 Hz, confirming the EKF predict-publish loop itself is slow.

**Observations (2026-03-25 bench test):**
```
/odom rate (stationary):  ~2 Hz   (heartbeat dedup — expected)
/odom rate (moving):      ~45 Hz  (dedup disabled — correct)
/imu/data_raw:            ~50 Hz  (correct)
/imu/data_filtered:       ~50 Hz  (Madgwick — correct)
/odometry/filtered:       ~2.5 Hz (expected 25 Hz — BUG)
```

**Input QoS (verified):**
- `/odom` publisher: RELIABLE / TRANSIENT_LOCAL
- `/imu/data_filtered` publisher: RELIABLE / VOLATILE
- EKF subscriber: BEST_EFFORT (compatible, should receive messages)

**Impact:**
- Nav2 controller runs at 10 Hz — needs odometry updates faster than 2.5 Hz
  for smooth trajectory tracking
- MPPI controller may produce jerky motion with stale state estimates
- SLAM loop closure accuracy may degrade

**Potential causes to investigate:**
1. QoS BEST_EFFORT subscriber dropping messages from RELIABLE publisher
2. robot_localization Jazzy version timer bug or regression
3. EKF only publishing on correction (not prediction) — internal behavior change
4. DDS middleware (CycloneDDS) discovery or transport issue on this hardware

**Workarounds to try:**
- Set `odom0_nodelay: true` and `imu0_nodelay: true` in `ekf_params.yaml`
- Test with FastDDS instead of CycloneDDS
- Check if `dynamic_process_noise_covariance: true` changes behavior

---

## ✅ Closed

*(No closed issues — see hardware-changelog.md for resolved improvements)*
