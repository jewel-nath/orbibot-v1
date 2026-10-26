# Hardware Node Issue Tracker

**Package:** `orbibot_hardware` (ROS 2 serial bridge, Python)
**Last Updated:** 2026-03-25

---

## 🔴 Open Bugs

### HW-BUG-1: EKF Output Rate ~2.5 Hz Instead of Configured 25 Hz
**Opened:** 2026-03-25
**Severity:** MEDIUM
**Affects:** `orbibot_localization` (robot_localization EKF), navigation performance

**Symptom:** `/odometry/filtered` publishes at ~2.5 Hz regardless of robot state
(stationary or moving). The EKF `frequency` parameter is set to 25.0 Hz in
`ekf_params.yaml`, but actual output rate is 10x lower.

**Impact:** Nav2 controller (10 Hz) needs faster odometry for smooth trajectory tracking.

**Potential causes:**
1. QoS BEST_EFFORT subscriber dropping from RELIABLE publisher
2. robot_localization Jazzy version timer bug
3. DDS middleware (CycloneDDS) transport issue

**Workarounds to try:**
- `odom0_nodelay: true` / `imu0_nodelay: true` in EKF config
- Test with FastDDS instead of CycloneDDS

---

## 🟡 Technical Debt

### HW-TD-1: rosmaster_driver.py uses print() instead of logging
**Severity:** LOW
**File:** `rosmaster_driver.py`

Error handling in serial methods uses `print()` which doesn't appear in ROS 2 logs.
Should use a Python `logging.Logger` instance or accept a callback for the hardware_node
to route through `self.get_logger()`.

---

### HW-TD-2: Circular buffer in USART ISR is populated but never read
**Severity:** LOW
**File:** firmware `hal_usart.c` (cross-reference: FW-ISSUE-1)

The firmware USART ISR stores every byte in both the protocol state machine AND a 256-byte
circular buffer. The read functions (`hal_usart_available`, `hal_usart_read_byte`) are never
called. This wastes 256 bytes RAM and ISR cycles.

---

## 💡 Improvement Ideas

### Performance
- **Batch serial writes:** Group PID + motion commands into single serial write when
  both arrive in the same cycle, reducing USB round-trips.

### Reliability
- **Serial health metric:** Expose firmware `g_rx_drop_count` and `g_unknown_cmd_count`
  as ROS diagnostics for monitoring protocol errors.
- **Watchdog topic:** Publish a heartbeat from the driver thread so hardware_node can
  detect thread death (not just serial disconnect).

### Extensibility
- **Plugin-based sensor abstraction:** If more sensor boards are added in the future,
  the serial protocol parsing could be abstracted behind a plugin interface.

---

## ✅ Closed

*(See hardware-changelog.md for resolved bugs and improvements)*
