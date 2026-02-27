/**
 * @file bsp_ssd1306.c
 * @brief SSD1306 OLED Display Driver (Text Mode Only)
 * @author Jewel Nath
 * @date 2025-11-30
 * 
 * Minimal SSD1306 driver for 128x32 OLED displays.
 * Supports text display only - all graphics functions removed to save flash.
 * 
 * Hardware: SSD1306 OLED (128x32 pixels) via I2C
 * Address: 0x3C
 */

#include "hal_ssd1306.h"
#include "string.h"

// I2C command/data control bytes
#define SSD1306_CMD_BYTE    0x00  // Command mode
#define SSD1306_DATA_BYTE   0x40  // Data mode

// Macros for I2C write
#define SSD1306_WRITE_CMD(cmd)   ssd1306_I2C_Write(SSD1306_I2C_ADDR, SSD1306_CMD_BYTE, (cmd))
#define SSD1306_WRITE_DATA(data) ssd1306_I2C_Write(SSD1306_I2C_ADDR, SSD1306_DATA_BYTE, (data))

// Display buffer (128 x 32 pixels = 512 bytes)
static uint8_t display_buffer[SSD1306_WIDTH * SSD1306_HEIGHT / 8];

// Display state
typedef struct
{
    uint16_t cursor_x;
    uint16_t cursor_y;
    uint8_t inverted;
    uint8_t initialized;
} ssd1306_state_t;

static ssd1306_state_t display_state;

/**
 * @brief Initialize SSD1306 OLED display
 * @return 1 on success, 0 on failure
 */
uint8_t SSD1306_Init(void)
{
    // Startup delay
    for (volatile uint32_t i = 0; i < 2500; i++);

    // Initialization sequence for 128x32 OLED
    SSD1306_WRITE_CMD(0xAE);  // Display off
    SSD1306_WRITE_CMD(0xD5);  // Set display clock divide ratio
    SSD1306_WRITE_CMD(0x80);  // Suggested ratio 0x80
    SSD1306_WRITE_CMD(0xA8);  // Set multiplex ratio
    SSD1306_WRITE_CMD(0x1F);  // 1/32 duty (32 rows)
    SSD1306_WRITE_CMD(0xD3);  // Set display offset
    SSD1306_WRITE_CMD(0x00);  // No offset
    SSD1306_WRITE_CMD(0x40);  // Set start line to 0
    SSD1306_WRITE_CMD(0x8D);  // Charge pump setting
    SSD1306_WRITE_CMD(0x14);  // Enable charge pump
    SSD1306_WRITE_CMD(0x20);  // Set memory addressing mode
    SSD1306_WRITE_CMD(0x02);  // Page addressing mode
    SSD1306_WRITE_CMD(0xA1);  // Set segment remap (flip horizontal)
    SSD1306_WRITE_CMD(0xC8);  // Set COM output scan direction (flip vertical)
    SSD1306_WRITE_CMD(0xDA);  // Set COM pins hardware configuration
    SSD1306_WRITE_CMD(0x02);  // Sequential COM pin config
    SSD1306_WRITE_CMD(0x81);  // Set contrast control
    SSD1306_WRITE_CMD(0xCF);  // Maximum contrast
    SSD1306_WRITE_CMD(0xD9);  // Set pre-charge period
    SSD1306_WRITE_CMD(0xF1);  // Phase 1: 1 DCLK, Phase 2: 15 DCLK
    SSD1306_WRITE_CMD(0xDB);  // Set VCOMH deselect level
    SSD1306_WRITE_CMD(0x40);  // ~0.77 x VCC
    SSD1306_WRITE_CMD(0x2E);  // Disable scroll
    SSD1306_WRITE_CMD(0xA4);  // Display follows RAM content
    SSD1306_WRITE_CMD(0xA6);  // Normal display (not inverted)
    SSD1306_WRITE_CMD(0xAF);  // Display on

    // Clear display buffer
    SSD1306_Fill(SSD1306_COLOR_BLACK);
    SSD1306_UpdateScreen();

    // Initialize state
    display_state.cursor_x = 0;
    display_state.cursor_y = 0;
    display_state.inverted = 0;
    display_state.initialized = 1;

    return 1;
}

/**
 * @brief Update OLED screen with buffer content
 */
void SSD1306_UpdateScreen(void)
{
    // Write buffer to display (8 pages for 32-pixel height)
    for (uint8_t page = 0; page < 4; page++)
    {
        SSD1306_WRITE_CMD(0xB0 + page);  // Set page address
        SSD1306_WRITE_CMD(0x00);         // Set lower column address
        SSD1306_WRITE_CMD(0x10);         // Set higher column address

        // Write one page (128 bytes)
        ssd1306_I2C_WriteMulti(SSD1306_I2C_ADDR, SSD1306_DATA_BYTE,
                               &display_buffer[SSD1306_WIDTH * page], SSD1306_WIDTH);
    }
}

/**
 * @brief Fill entire screen with color
 * @param color SSD1306_COLOR_BLACK or SSD1306_COLOR_WHITE
 */
void SSD1306_Fill(SSD1306_COLOR_t color)
{
    memset(display_buffer, (color == SSD1306_COLOR_BLACK) ? 0x00 : 0xFF, sizeof(display_buffer));
}

/**
 * @brief Draw a single pixel
 * @param x X coordinate (0-127)
 * @param y Y coordinate (0-31)
 * @param color Pixel color
 */
static void draw_pixel(uint16_t x, uint16_t y, SSD1306_COLOR_t color)
{
    // Bounds check
    if (x >= SSD1306_WIDTH || y >= SSD1306_HEIGHT)
        return;

    // Handle inverted mode
    if (display_state.inverted)
        color = (SSD1306_COLOR_t)!color;

    // Set or clear pixel in buffer
    if (color == SSD1306_COLOR_WHITE)
        display_buffer[x + (y / 8) * SSD1306_WIDTH] |= (1 << (y % 8));
    else
        display_buffer[x + (y / 8) * SSD1306_WIDTH] &= ~(1 << (y % 8));
}

/**
 * @brief Set cursor position for text
 * @param x X coordinate in pixels
 * @param y Y coordinate in pixels
 */
void SSD1306_GotoXY(uint16_t x, uint16_t y)
{
    display_state.cursor_x = x;
    display_state.cursor_y = y;
}

/**
 * @brief Print a single character
 * @param ch Character to print
 * @param font Pointer to font definition
 * @param color Text color
 * @return Character printed, or 0 if out of bounds
 */
char SSD1306_Putc(char ch, FontDef_t *font, SSD1306_COLOR_t color)
{
    // Check if character fits on screen
    if (SSD1306_WIDTH <= (display_state.cursor_x + font->FontWidth) ||
        SSD1306_HEIGHT <= (display_state.cursor_y + font->FontHeight))
    {
        return 0;  // Out of bounds
    }

    // Draw character from font data
    for (uint32_t row = 0; row < font->FontHeight; row++)
    {
        uint16_t font_byte = font->data[(ch - 32) * font->FontHeight + row];
        
        for (uint32_t col = 0; col < font->FontWidth; col++)
        {
            if ((font_byte << col) & 0x8000)
                draw_pixel(display_state.cursor_x + col, display_state.cursor_y + row, color);
            else
                draw_pixel(display_state.cursor_x + col, display_state.cursor_y + row, (SSD1306_COLOR_t)!color);
        }
    }

    // Advance cursor
    display_state.cursor_x += font->FontWidth;

    return ch;
}

/**
 * @brief Print a string
 * @param str String to print
 * @param font Pointer to font definition
 * @param color Text color
 * @return 0 on success, or first character that didn't fit
 */
char SSD1306_Puts(char *str, FontDef_t *font, SSD1306_COLOR_t color)
{
    while (*str)
    {
        if (SSD1306_Putc(*str, font, color) != *str)
            return *str;  // Character didn't fit
        
        str++;
    }

    return 0;  // Success
}

/**
 * @brief Write single byte to I2C device
 * @param address I2C device address
 * @param reg Register/command byte
 * @param data Data byte to write
 */
void ssd1306_I2C_Write(uint8_t address, uint8_t reg, uint8_t data)
{
    i2cWrite(address, reg, 1, &data);
}

/**
 * @brief Write multiple bytes to I2C device
 * @param address I2C device address
 * @param reg Register/command byte
 * @param data Pointer to data buffer
 * @param count Number of bytes to write
 */
void ssd1306_I2C_WriteMulti(uint8_t address, uint8_t reg, uint8_t *data, uint16_t count)
{
    i2cWrite(address, reg, count, data);
}
