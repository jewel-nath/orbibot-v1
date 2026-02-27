/**
 * @file hal_adc.h
 * @brief ADC Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef HAL_ADC_H
#define HAL_ADC_H

#include <stdint.h>

int hal_adc_init(void);
uint16_t hal_adc_read_battery(void);

#endif // HAL_ADC_H
