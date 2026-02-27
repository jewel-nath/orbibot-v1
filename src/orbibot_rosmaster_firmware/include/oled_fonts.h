/**
 * @file oled_fonts.h
 * @brief OLED Font Library
 * @author Jewel Nath
 * @date 2025-11-30
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
