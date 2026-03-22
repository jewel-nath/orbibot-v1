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
// MUST match the PWM forward direction defined in hal_timer.c motor_map[]:
//   M1 (FL): -1  |  M2 (BL): -1  |  M3 (FR): +1  |  M4 (BR): +1
// If hardware wiring changes, update both this table AND hal_timer.c:motor_map[].
// Verify with: python3 tests/test_encoder.py (spin each wheel forward, check sign)
static const int8_t encoder_direction[4] = { -1, -1, 1, 1 };

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
 * - M1 (FL): inverted (-1), M2 (BL): normal (+1)
 * - M3 (FR): normal (+1),   M4 (BR): inverted (-1)
 */
int16_t encoder_read_delta(uint8_t encoder)
{
    if (encoder >= 4) return 0;

    int16_t delta = hal_timer_read_encoder_delta(encoder);
    delta *= encoder_direction[encoder];

    encoder_accumulated[encoder] += delta;
    return delta;
}

void encoder_get_all(int32_t *counts)
{
    for (int i = 0; i < 4; i++)
    {
        counts[i] = encoder_accumulated[i];
    }
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

void encoder_reset(uint8_t encoder)
{
    if (encoder >= 4) return;
    encoder_accumulated[encoder] = 0;
    hal_timer_reset_encoder(encoder);
}
