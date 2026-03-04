# OrbiBot Firmware — Open Issues & Future Work

**Last updated**: 2026-03-04
**Firmware Version**: v2.0.0

> All issues from the deep audit (2026-03-04) have been resolved.
> See [firmware-changelog.md](firmware-changelog.md) for the full fix history.

---

## Open Improvements

### PERF-1: Fixed-Point PID — STM32F103 Has No FPU

**Priority**: HIGH
**Files**: `control/pid_controller.c`, `tasks/task_control.c`

All PID calculations use `float` — every float op is a ~20-50 cycle software library call on Cortex-M3. The PID loop runs at 100Hz with 4 motors.

**Approach**:
- `typedef int32_t fixed_t` with Q16.16 format
- `fixed_mul(a, b) = ((int64_t)a * b) >> 16`
- Keep float only for configuration API (convert to fixed-point at set time)
- Estimated ~50% CPU reduction in control loop

---

### PERF-3: DMA for UART RX

**Priority**: MEDIUM
**File**: `hal/hal_usart.c`

UART receive uses per-byte RXNE interrupts — up to ~11,520 ISRs/second at 115200 baud. Each interrupt calls `protocol_receive_byte()`.

**Approach**: DMA1 Channel5 (USART1_RX) circular buffer. Process received bytes in bulk from the communication task using `DMA_GetCurrDataCounter()`.

---

### M1: Magnetometer Complementary Filter for Yaw

**Priority**: MEDIUM
**File**: `tasks/task_imu.c`

Yaw is pure gyro integration (`g_yaw += gyro_z * dt`) — drifts over time. The ICM-20948 magnetometer is read and sent to ROS but never used for on-board yaw correction.

**Approach**: Complementary filter blending gyro and magnetometer heading:
```c
yaw = 0.98f * (yaw + gyro_z * dt) + 0.02f * mag_yaw;
```

---

### I2: Encoder Velocity EMA Filtering

**Priority**: LOW
**File**: `tasks/task_control.c`

Raw encoder delta is used directly as measured wheel velocity. Single-tick noise spikes pass through to the PID.

**Approach**: Low-pass EMA filter on `wheel_speed_mm_s`:
```c
filtered = 0.7f * new_speed + 0.3f * filtered_prev;
```

---

### I3: Gyro Calibration — Move to RTOS Task

**Priority**: LOW
**File**: `drivers/imu_driver.c`

`imu_calibrate()` collects 1000 samples × 1ms = ~1 second busy-wait before the FreeRTOS scheduler starts.

**Approach**: Reduce samples to 200, or move calibration to a startup task using `vTaskDelay()`.

---

## Testing Gaps

> Test improvement ideas — see also `tests/` for existing Python test scripts.

### TEST-1: Host-Side Unit Tests for Core Algorithms

**Priority**: HIGH

Pure functions that can be tested on x86 without hardware:
- PID controller: `pid_calculate_incremental()`, `pid_get_gains_for_speed()`
- Mecanum kinematics: `mecanum_inverse_kinematics()`, `mecanum_forward_kinematics()`
- Odometry integration: `odometry_update()`
- Protocol parsing: `protocol_receive_byte()` state machine, `protocol_calculate_checksum()`

---

### TEST-2: Protocol Double-Buffer Stress Test

**Priority**: MEDIUM

Test with: back-to-back packets, packets during auto-report TX, maximum-length packets, corrupted packets.

---

### TEST-3: Watchdog Recovery Verification

**Priority**: MEDIUM

Verify watchdog resets MCU when: `task_control` hangs, `task_imu` blocks on SPI, heap exhaustion.

---

### TEST-4: Flash Storage Wear/Corruption Test

**Priority**: LOW

Verify: behavior after thousands of writes, recovery from power loss during erase, corrupted checksum handling.

---

*For resolved issues and full fix history, see [firmware-changelog.md](firmware-changelog.md).*
