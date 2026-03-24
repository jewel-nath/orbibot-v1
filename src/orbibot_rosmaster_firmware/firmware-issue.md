# Firmware Issue Tracker

**Package:** `orbibot_rosmaster_firmware` (STM32F103RCT6, v2.0.0)
**Last Updated:** 2026-03-25

---

## 🔴 Open

*(none)*

---

## ✅ Closed

### FW-BUG-2: Accelerometer Z Reads 1.566× Gravity (Scale Factor Bug) ✅
**Closed:** 2026-03-25
**Severity:** HIGH
**File:** `src/drivers/imu_driver.c`

**Root cause:** ICM-20948 on this hardware produces 25644 raw ADC counts per 1g
instead of the nominal 16384 (±2g range). ACCEL_CONFIG register readback confirmed
0x31 (correct), but chip sensitivity is persistently 1.566× off — likely a silicon
lot variation or internal trim difference.

**Fix applied:** Empirical scale in `imu_driver_init()`:
```c
// Before (wrong): accel_scale = 2.0f / 32768.0f * 9.80665f = 0.000599
// After (correct): 1g = 25644 counts measured at rest
accel_scale = 9.80665f / 25644.0f;  // = 0.000382 m/s²/count
```

**Verification result (2026-03-25, 170 samples, robot flat):**
```
ax = 0.004 m/s²   ay = 0.127 m/s²   az = 9.797 m/s²
|accel| = 9.798 m/s²  (expected 9.807 m/s²)
Error: 0.09%  ✓
```

---

### FW-BUG-3: IWDG Reset Loop on Production Firmware ✅
**Closed:** 2026-03-25
**Severity:** HIGH
**File:** `src/main.c`

**Root cause:** STM32F103 LSI tolerance is 30–60 kHz. At 60 kHz the IWDG timeout
shrinks from 5.0s to 3.33s. The startup sequence (imu_calibrate 1000 samples ≈ 1s,
other init ≈ 0.6s) plus 2 MonitorTask cycles before first watchdog feed ≈ 3.5s
exceeds 3.33s on fast-LSI hardware, causing a persistent reset loop.

**Fix applied:** Added `hal_watchdog_feed()` at the end of `main()` just before
`vTaskStartScheduler()`. This resets the 5s window after init completes, so
MonitorTask's first feed (at t=1s into FreeRTOS) is safely within budget.

---

### FW-BUG-4: Checksum Mismatch — All Incoming Commands Silently Rejected ✅
**Closed:** 2026-03-25
**Severity:** HIGH
**File:** `src/communication/protocol.c`

**Root cause:** `protocol_calculate_checksum()` summed bytes from index 1
(including DEVICE_ID = 0xFC), but both the ROS 2 hardware driver and the Python
test library use a formula that effectively sums from index 2 (LENGTH onward).
Result: every checksum comparison failed; `ENABLE_CHECKSUM=1` silently dropped
all incoming commands, disabling auto-report and all control.

**Fix applied:** Changed loop start from `i = 1` to `i = 2`:
```c
// Before: for (uint8_t i = 1; ...) → includes Device_ID (0xFC) → mismatch
// After:  for (uint8_t i = 2; ...) → sums Length+Func+Data → matches host
for (uint8_t i = 2; i < length - 1; i++)
```

---

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
