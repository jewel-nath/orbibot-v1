# OrbiBot Firmware Issues and Improvements

This document tracks known issues, potential bugs, and areas for improvement in the OrbiBot ROSMaster firmware.

## Current Status: Stable
**Last Review**: March 2026
**Firmware Version**: v2.0.0

---

## Known Issues

### Issue #1: IMU Magnetometer Calibration Limited
**Severity**: Low  
**Location**: `drivers/imu_driver.c`, `communication/protocol.c`

**Description**:
The current implementation only supports hard-iron offset calibration for the magnetometer. Soft-iron matrix calibration is defined in the structure but not fully implemented via the protocol.

**Current Code**:
```c
// In protocol.c - only hard-iron offsets are configurable
void protocol_handle_set_mag_cal(const uint8_t *data) {
    // Only receives 6 bytes (3 offsets × 2 bytes)
    // Soft-iron matrix (9 floats) not configurable via protocol
}
```

**Impact**:
- Magnetometer accuracy may be reduced in environments with magnetic interference
- Yaw drift correction may be less effective

**Recommended Fix**:
Extend the protocol to support full soft-iron matrix calibration or implement automatic ellipsoid fitting calibration routine.

---

### Issue #2: Yaw Control Activation Threshold Hardcoded
**Severity**: Low  
**Location**: `tasks/task_control.c`

**Description**:
The yaw control activation threshold is hardcoded to 0.05 m/s in the code:

```c
uint8_t should_yaw_control = (fabsf(target_local.omega) < 0.01f) &&
                              (speed_magnitude > 0.05f);  // Hardcoded!
```

**Impact**:
- Cannot tune via protocol without recompiling
- May not be optimal for all floor surfaces

**Recommended Fix**:
Add protocol command to configure yaw control threshold, similar to PID gains.

---

### Issue #3: Encoder Direction Configuration Not Runtime-Configurable
**Severity**: Medium  
**Location**: `drivers/encoder_driver.c`

**Description**:
Motor direction inversion is compile-time configured via `MOTOR1_INVERTED` etc. flags in config. If motors are wired differently, firmware must be recompiled.

**Current**:
```c
// In encoder_driver.c
#ifdef MOTOR1_INVERTED
    delta = -delta;
#endif
```

**Impact**:
- Difficult to troubleshoot motor direction issues in the field
- Requires firmware rebuild for hardware variations

**Recommended Fix**:
Store direction flags in flash storage and make configurable via protocol.

---

### Issue #4: No Checksum on Flash Storage
**Severity**: Medium  
**Location**: `drivers/flash_storage.c`

**Description**:
Flash storage writes PID gains and calibration data without a checksum or CRC. Corrupted flash data (due to power loss during write) could be loaded as valid.

**Current**:
```c
// No checksum validation in flash_storage_load()
```

**Impact**:
- Corrupted PID gains could cause erratic motor behavior
- Difficult to detect flash corruption

**Recommended Fix**:
Add CRC-16 or similar checksum to flash storage structure.

---

### Issue #5: Watchdog Feed in task_monitoring May Not Be Sufficient
**Severity**: Low  
**Location**: `tasks/task_monitoring.c`

**Description**:
The watchdog is fed every 1 second in task_monitoring. If task_control hangs (most critical task), watchdog may not trigger if task_monitoring continues running.

**Current**:
```c
// task_monitoring feeds watchdog every 1s
// But what if only task_control hangs?
hal_watchdog_feed();
```

**Impact**:
- Critical control task hang may not be detected
- Robot could continue with stuck motors

**Recommended Fix**:
Feed watchdog from task_control (which runs at 100Hz) or implement task health monitoring that checks all critical tasks.

---

### Issue #6: OLED Display Stub Implementation
**Severity**: Low  
**Location**: `drivers/oled_driver.c`

**Description**:
OLED driver is marked as "stub" - functions exist but may not be fully functional.

**Current Status**:
- Driver skeleton present
- Hardware I2C conflicts with encoder TIM4
- Software I2C implemented but untested

**Impact**:
- Display functionality not available for debugging

**Recommended Fix**:
Complete software I2C implementation and test with actual OLED hardware.

---

### Issue #7: Motor PWM Frequency Not Runtime-Configurable
**Severity**: Low  
**Location**: `hal/hal_timer.c`

**Description**:
PWM frequency is fixed at 20kHz in hardware initialization. Cannot be changed without recompiling.

**Impact**:
- Cannot tune for different motor types
- 20kHz may not be optimal for all applications

**Recommended Fix**:
Add protocol command to adjust PWM frequency (within safe limits).

---

### Issue #8: No Motor Current Sensing
**Severity**: Medium  
**Location**: Hardware limitation

**Description**:
The firmware does not have access to motor current feedback. Stall detection and current limiting are not possible.

**Impact**:
- Cannot detect motor stall conditions
- Risk of motor/driver damage during stall
- No overcurrent protection in firmware

**Note**: This is primarily a hardware limitation - the ROSMaster board does not have current sense resistors.

**Recommended Fix**:
Consider adding external current sensors for future hardware revisions.

---

## Performance Improvements

### Improvement #1: Reduce SPI Transactions in IMU Reading
**Current**: Multiple SPI transactions for gyro/accel, then mag separately  
**Better**: Single burst read of all sensor data

**Estimated Gain**: ~20% reduction in IMU task time

---

### Improvement #2: Optimize PID Calculation
**Current**: Floating-point PID in control loop  
**Better**: Fixed-point arithmetic for PID (significant speedup on F103 without FPU)

**Estimated Gain**: ~50% faster control loop, allowing higher rate or more features

---

### Improvement #3: DMA for Serial Communication
**Current**: Byte-by-byte UART handling  
**Better**: DMA-based UART with circular buffer

**Estimated Gain**: Lower CPU usage, fewer interrupts

---

## Code Quality Notes

### Note #1: Inconsistent Naming Convention
Some files use `snake_case` (good) but some variables mix conventions. All code should follow the project coding standards.

### Note #2: Magic Numbers
Some constants are hardcoded without explanation:
```c
// What does 0x5F mean?
if (state == 0x5F) {  // Should be SAVE_VERIFY constant
```

### Note #3: Commented-Out Code
Several files have commented-out debug code that should be removed or properly conditioned.

---

## Testing Gaps

### Gap #1: No Unit Tests
The firmware lacks unit tests for:
- PID controller algorithms
- Kinematics calculations
- Protocol parsing

### Gap #2: No Hardware-in-Loop Testing
No automated testing with actual motors/sensors connected.

### Gap #3: Limited Edge Case Testing
- No test for maximum velocity commands
- No test for encoder overflow
- No test for communication errors

---

## Documentation Improvements Needed

1. **API Documentation**: Doxygen comments incomplete in some files
2. **Protocol Specification**: Binary protocol not fully documented
3. **Calibration Guide**: Step-by-step calibration procedures missing
4. **Tuning Guide**: PID tuning methodology not documented

---

## Resolved Issues (Historical)

### Resolved: SPI2 Timeout Protection (December 2025)
Added timeout to all SPI operations to prevent infinite loops.

### Resolved: FreeRTOS Task Stack Sizes (January 2026)
Increased communication task stack from 256 to 512 words to prevent stack overflow during flash operations.

### Resolved: Magnetometer DRDY Handling (February 2026)
Added last-valid-reading cache to prevent zero-value spikes when DRDY not set.

---

## How to Contribute Fixes

1. Create a branch: `git checkout -b fix/issue-number-description`
2. Make changes with clear commit messages
3. Test on actual hardware
4. Update this document when issue is resolved
5. Submit pull request with detailed description

---

## Contact

For questions about these issues:
- GitHub Issues: [OrbiBot Repository](https://github.com/your-repo/orbibot_ws/issues)
- Maintainer: Jewel Nath