# Firmware Issue Tracker

**Package:** `orbibot_rosmaster_firmware` (STM32F103RCT6, v2.0.0)
**Last Updated:** 2026-03-24

---

## 🔴 Open

### FW-BUG-2: Accelerometer Z Reads 1.566× Gravity (Scale Factor Bug)
**Severity:** HIGH
**File:** `src/drivers/imu_driver.c` (accel_scale computation or ACCEL_CONFIG register write)

**Symptoms:**
- Accel Z = 15356 milli-m/s² (expected 9807)
- Accel magnitude = 15.36 m/s² (expected 9.81)
- Ratio = 1.566× — consistent across 100+ samples
- Gyro readings are correct (near zero when stationary) — only accel affected

**Analysis:**
```
Firmware sets: accel_scale = 2.0f / 32768.0f * 9.80665f = 0.000599
Firmware writes: ACCEL_CONFIG = 0x31 (±2g range, Bank 2)
Expected at ±2g: 1g = 16384 raw ADC counts → 16384 × 0.000599 = 9.81 m/s²
Back-calculated raw ADC from output: 25644 counts (1.566× expected)
```

This means either:
1. **ACCEL_CONFIG register write to Bank 2 silently failed** — chip stayed at a
   non-standard sensitivity (raw=25644 for 1g instead of 16384)
2. **SPI read-back would confirm** — add register verify after write

**Impact:**
- Madgwick filter gets wrong gravity magnitude → orientation error
- EKF accelerometer data is 1.566× too large
- Roll/pitch estimation off by `asin(1/1.566)` ≈ some degrees

**Proposed Fix (choose one):**
```c
// Option A: Empirical scale (quick fix — measure what hardware actually returns)
accel_scale = 9.80665f / 25644.0f;  // 1g = 25644 raw counts (measured)

// Option B: Read-back and verify register (proper fix)
imu_write_register(ICM20948_ACCEL_CONFIG, 0x31);
uint8_t readback = imu_read_register(ICM20948_ACCEL_CONFIG);
if (readback != 0x31) {
    BOOT_PRINTF("[IMU] ACCEL_CONFIG write FAILED! wrote 0x31, read 0x%02X\n", readback);
    // Compute scale from actual range
}
```

**Verification after fix:**
```bash
# After flashing, run:
python3 -c "  # (inline script from test session)
# Accel Z should be ~9810 milli-m/s²
# Magnitude should be ~9807 milli-m/s²
"
```

---

## ✅ Closed

### FW-BUG-1: Encoder Direction Values — VERIFIED ✅
**Closed:** 2026-03-24
**Verification result:** Forward command → all 4 encoders positive delta (automated test).
```
M1 (FL): delta = +2356  → OK ✓
M2 (BL): delta = +2651  → OK ✓
M3 (FR): delta = +2442  → OK ✓
M4 (BR): delta = +2155  → OK ✓
```

---

## See also
- `firmware-changelog.md` — resolved improvements
- `improve-plan.md` — comparison with lgdxrobot2
