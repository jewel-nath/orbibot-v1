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
 * Applies direction correction for ROSMaster V3.0 motor wiring:
 * - M1 (encoder 0): Normal   (forward = positive)
 * - M2 (encoder 1): Inverted (left side, motor mounted opposite)
 * - M3 (encoder 2): Inverted (right side, encoder phase swapped)
 * - M4 (encoder 3): Normal   (right side)
 *
 * Verified by manual wheel rotation test: forward rotation increases count.
 * See HARDWARE_DOC.md for motor/encoder wiring details.
 */
int16_t encoder_read_delta(uint8_t encoder)
{
    if (encoder >= 4) return 0;

    int16_t delta = hal_timer_read_encoder_delta(encoder);

    // Apply direction correction for ROSMaster V3.0 motor configuration
    // G5: Inverted after HAL encoder delta fix (previous inversions compensated for HAL bug)
    switch (encoder)
    {
        case 0:  // M1 (Front-Left) - inverted
            delta = -delta;
            break;
        case 1:  // M2 (Back-Left) - normal
            break;
        case 2:  // M3 (Front-Right) - normal
            break;
        case 3:  // M4 (Back-Right) - inverted
            delta = -delta;
            break;
    }

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
