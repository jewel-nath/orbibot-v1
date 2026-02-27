/**
 * @file oled_driver.c
 * @brief OLED Driver Implementation (SSD1306)
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "oled_driver.h"
#include "hal_ssd1306.h"
#include <stdio.h>
#include <string.h>

/**
 * @brief Initialize OLED driver
 * @return 0 on success, -1 on failure
 */
int oled_driver_init(void)
{
    // Initialize SSD1306 OLED
    uint8_t result = SSD1306_Init();

    if (result == 0)
    {
        return -1;
    }

    // Show initialization message
    oled_show_init();
    return 0;
}

/**
 * @brief Clear OLED display
 */
void oled_clear(void)
{
    SSD1306_Fill(SSD1306_COLOR_BLACK);
}

/**
 * @brief Print text at specific position
 * @param col Column position (pixels)
 * @param row Row position (pixels)
 * @param str String to print
 */
void oled_print(uint8_t col, uint8_t row, const char *str)
{
    SSD1306_GotoXY(col, row);
    SSD1306_Puts((char*)str, &Font_7x10, SSD1306_COLOR_WHITE);
}

/**
 * @brief Update OLED display
 */
void oled_update(void)
{
    SSD1306_UpdateScreen();
}

/**
 * @brief Show custom status message (2 lines)
 * @param line1 First line text
 * @param line2 Second line text
 */
void oled_show_status(const char *line1, const char *line2)
{
    SSD1306_Fill(SSD1306_COLOR_BLACK);
    
    if (line1)
    {
        SSD1306_GotoXY(0, 0);
        SSD1306_Puts((char*)line1, &Font_7x10, SSD1306_COLOR_WHITE);
    }
    
    if (line2)
    {
        SSD1306_GotoXY(0, 12);
        SSD1306_Puts((char*)line2, &Font_7x10, SSD1306_COLOR_WHITE);
    }
    
    SSD1306_UpdateScreen();
}

/**
 * @brief Show initialization message
 */
void oled_show_init(void)
{
    oled_show_status("Initializing...", "OrbiBot v1.0");
}

/**
 * @brief Show ready message
 */
void oled_show_ready(void)
{
    oled_show_status("OrbiBot v1.0", "Ready!");
}

/**
 * @brief Show low voltage warning
 */
void oled_show_low_voltage(void)
{
    oled_show_status("WARNING", "Low Voltage");
}

/**
 * @brief Show over voltage warning
 */
void oled_show_over_voltage(void)
{
    oled_show_status("WARNING", "Over Voltage");
}

/**
 * @brief Show error message
 * @param error_msg Error message to display
 */
void oled_show_error(const char *error_msg)
{
    oled_show_status("ERROR", error_msg);
}
