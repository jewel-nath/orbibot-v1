/**
 * @file oled_fonts.h
 * @brief OLED Font Library
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * The Font7x10 table it declares is from afiskon/stm32-ssd1306 (ssd1306_fonts.c),
 * https://github.com/afiskon/stm32-ssd1306
 * Copyright (c) 2018 Aleksander Alekseev. MIT License: see LICENSES/stm32-ssd1306.txt.
 */

#ifndef OLED_FONTS_H
#define OLED_FONTS_H

#include "stm32f10x.h"

/**
 * @brief Font structure
 */
typedef struct {
    uint8_t FontWidth;    /*!< Font width in pixels */
    uint8_t FontHeight;   /*!< Font height in pixels */
    const uint16_t *data; /*!< Pointer to font data array */
} FontDef_t;

/**
 * @brief 7 x 10 pixels font size structure
 */
extern FontDef_t Font_7x10;

#endif // OLED_FONTS_H
