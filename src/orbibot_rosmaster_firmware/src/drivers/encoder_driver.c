/**
 * @file encoder_driver.c
 * @brief Encoder Driver Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "encoder_driver.h"
#include "hal_timer.h"

// Accumulated encoder counts for odometry
static int32_t encoder_accumulated[4] = {0, 0, 0, 0};

// Direction correction table for ROSMaster V3.0 motor wiring.
// Each entry is +1 or -1 to make positive encoder counts mean forward wheel rotation.
// MUST match the PWM forward direction defined in hal_timer.c motor_map[].
//
// FW-BUG-5 (2026-03-25): was { -1, -1, 1, 1 } — M2 and M4 were inverted.
// Root cause: the header comment claimed M2=-1, M4=+1, contradicting the
// function-level comment below (M2=+1, M4=-1). Test confirmed:
//   send_motion(vx=0.3) → M1=+2402 OK, M2=-14695 FAIL, M3=+2388 OK, M4=-11610 FAIL.
//   Wrong sign causes PID to receive inverted feedback → integrator runs away
//   (6× overspeed on M2/M4 vs M1/M3).
// Fix: corrected M2 from -1 → +1 and M4 from +1 → -1.
//
// Summary — verified directions (hardware, motor spinning forward):
//   M1 (FL): raw counts DOWN → correction -1 → reported positive ✓
//   M2 (BL): raw counts UP   → correction +1 → reported positive ✓
//   M3 (FR): raw counts UP   → correction +1 → reported positive ✓
//   M4 (BR): raw counts DOWN → correction -1 → reported positive ✓
//
// If hardware wiring changes, re-run: python3 tests/test_encoder.py
static const int8_t encoder_direction[4] = { -1, 1, 1, -1 };

int encoder_driver_init(void)
{
    // Encoder hardware (TIM2/3/4/5 quadrature decoders) is initialized by
    // hal_timer_init() in main.c, which configures both PWM and encoder timers
    // together. This function resets the software-accumulated counters only.
    for (int i = 0; i < 4; i++)
    {
        encoder_accumulated[i] = 0;
    }
    return 0;
}

/**
 * @brief Read encoder delta with direction correction
 *
 * Direction correction is defined in encoder_direction[] above:
 * - M1 (FL): inverted (-1) — raw counts DOWN on forward rotation
 * - M2 (BL): normal   (+1) — raw counts UP   on forward rotation
 * - M3 (FR): normal   (+1) — raw counts UP   on forward rotation
 * - M4 (BR): inverted (-1) — raw counts DOWN on forward rotation
 */
int16_t encoder_read_delta(uint8_t encoder)
{
    if (encoder >= 4) return 0;

    int16_t delta = hal_timer_read_encoder_delta(encoder);
    delta *= encoder_direction[encoder];

    encoder_accumulated[encoder] += delta;
    return delta;
}

void encoder_reset_all(void)
{
    for (int i = 0; i < 4; i++)
    {
        encoder_accumulated[i] = 0;
        hal_timer_reset_encoder(i);
    }
}

int32_t encoder_get_count(uint8_t encoder)
{
    if (encoder >= 4) return 0;
    return encoder_accumulated[encoder];
}
