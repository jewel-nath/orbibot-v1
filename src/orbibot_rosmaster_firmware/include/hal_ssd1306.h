/**
 * @file hal_ssd1306.h
 * @brief SSD1306 OLED Display Driver Header (Text Mode Only)
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef HAL_SSD1306_H
#define HAL_SSD1306_H

#include "oled_fonts.h"
#include "stm32f10x.h"

// SSD1306 configuration
#define SSD1306_I2C_ADDR    0x3C
#define SSD1306_WIDTH       128
#define SSD1306_HEIGHT      32

// Color definitions
typedef enum {
    SSD1306_COLOR_BLACK = 0x00,  // Black color, no pixel
    SSD1306_COLOR_WHITE = 0x01   // White color, pixel is set
} SSD1306_COLOR_t;

// Public functions
uint8_t SSD1306_Init(void);
void SSD1306_UpdateScreen(void);
void SSD1306_Fill(SSD1306_COLOR_t color);
void SSD1306_GotoXY(uint16_t x, uint16_t y);
char SSD1306_Putc(char ch, FontDef_t *font, SSD1306_COLOR_t color);
char SSD1306_Puts(char *str, FontDef_t *font, SSD1306_COLOR_t color);

// I2C helper functions
void ssd1306_I2C_Write(uint8_t address, uint8_t reg, uint8_t data);
void ssd1306_I2C_WriteMulti(uint8_t address, uint8_t reg, uint8_t *data, uint16_t count);

#endif // HAL_SSD1306_H
