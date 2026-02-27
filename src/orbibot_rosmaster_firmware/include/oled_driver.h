/**
 * @file oled_driver.h
 * @brief OLED Driver Interface (SSD1306)
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef OLED_DRIVER_H
#define OLED_DRIVER_H

#include <stdint.h>

// Initialize OLED driver
int oled_driver_init(void);

// Low-level functions
void oled_clear(void);
void oled_print(uint8_t col, uint8_t row, const char *str);
void oled_update(void);

// Status message functions
void oled_show_status(const char *line1, const char *line2);
void oled_show_init(void);
void oled_show_ready(void);
void oled_show_low_voltage(void);
void oled_show_over_voltage(void);
void oled_show_error(const char *error_msg);

#endif // OLED_DRIVER_H
