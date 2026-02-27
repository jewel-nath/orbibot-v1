/**
 * @file hal_i2c.h
 * @brief I2C Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef HAL_I2C_H
#define HAL_I2C_H

#include <stdint.h>

int hal_i2c_init(void);
int i2cWrite(uint8_t address, uint8_t reg, uint16_t count, uint8_t *data);
int i2cRead(uint8_t address, uint8_t reg, uint16_t count, uint8_t *data);

#endif // HAL_I2C_H
