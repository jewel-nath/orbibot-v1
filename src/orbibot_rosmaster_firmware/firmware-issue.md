# Firmware Issue Tracker

**Package:** `orbibot_rosmaster_firmware` (STM32F103RCT6, v2.0.0)
**Last Updated:** 2026-03-22

---

## 🔴 Open — Requires Hardware

### FW-BUG-1: Encoder Direction Values Need Hardware Verification
**Severity:** HIGH
**File:** `src/drivers/encoder_driver.c:16`

**Status:** Code fix applied in commit (changed `{-1, 1, 1, -1}` → `{-1, -1, 1, 1}` to align
M2 and M4 with their PWM direction flags in `hal_timer.c:motor_map[]`). **Must be verified
on hardware before this can be closed.**

**Verification procedure:**
```bash
cd src/orbibot_rosmaster_firmware/tests
python3 test_encoder.py    # Spin each wheel forward by hand, confirm count is positive
python3 test_motor_direction.py  # Run motors forward, confirm encoders count up
```

Expected: all four motors show positive encoder delta when commanded forward.
If any motor shows negative delta when commanded forward → that motor's entry in
`encoder_direction[]` needs to be flipped.

---

## ✅ All other issues resolved — see firmware-changelog.md
