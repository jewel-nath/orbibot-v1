/**
 * @file hal_spi.c
 * @brief SPI Hardware Abstraction Layer Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "hal_spi.h"
#include "stm32f10x.h"
#include "orbibot_config.h"
#include <stddef.h>

// SPI timeout for safety (prevent infinite loops like in RGB DMA issue)
#define SPI_TIMEOUT_COUNT   0x1000

/**
 * @brief Initialize SPI2 for IMU communication
 *
 * Configuration:
 * - SPI2: PB13 (SCK), PB14 (MISO), PB15 (MOSI)
 * - CS: PB12 (GPIO manual control)
 * - Clock: APB1/4 = 36MHz/4 = 9MHz (close to 8MHz target)
 * - Mode: Mode 0 (CPOL=0, CPHA=0) - compatible with ICM-20948
 * - 8-bit data, MSB first
 */
int hal_spi_init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    SPI_InitTypeDef SPI_InitStructure;

    // Enable clocks for GPIOB and SPI2
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_SPI2, ENABLE);

    // Configure SPI2 pins: SCK (PB13), MISO (PB14), MOSI (PB15)
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_13 | GPIO_Pin_15;  // SCK, MOSI
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_14;  // MISO
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    // Configure CS pin (PB12) as GPIO output (manual control)
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_12;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    // Deselect device (CS high)
    GPIO_SetBits(GPIOB, GPIO_Pin_12);

    // Configure SPI2
    SPI_InitStructure.SPI_Direction = SPI_Direction_2Lines_FullDuplex;
    SPI_InitStructure.SPI_Mode = SPI_Mode_Master;
    SPI_InitStructure.SPI_DataSize = SPI_DataSize_8b;
    SPI_InitStructure.SPI_CPOL = SPI_CPOL_Low;   // Clock idle low (Mode 0)
    SPI_InitStructure.SPI_CPHA = SPI_CPHA_1Edge; // Sample on first edge (Mode 0)
    SPI_InitStructure.SPI_NSS = SPI_NSS_Soft;    // Software CS control
    SPI_InitStructure.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_8;  // APB1/8 = 4.5MHz (ICM-20948 max 7MHz)
    SPI_InitStructure.SPI_FirstBit = SPI_FirstBit_MSB;
    SPI_InitStructure.SPI_CRCPolynomial = 7;
    SPI_Init(SPI2, &SPI_InitStructure);

    // Enable SPI2
    SPI_Cmd(SPI2, ENABLE);

    return 0;
}

/**
 * @brief Select SPI device (assert CS low)
 */
void hal_spi_select(void)
{
    GPIO_ResetBits(GPIOB, GPIO_Pin_12);  // CS low
    // Small delay to meet CS setup time
    for (volatile int i = 0; i < 10; i++);
}

/**
 * @brief Deselect SPI device (release CS high)
 */
void hal_spi_deselect(void)
{
    // Small delay to meet CS hold time
    for (volatile int i = 0; i < 10; i++);
    GPIO_SetBits(GPIOB, GPIO_Pin_12);  // CS high
}

/**
 * @brief Transfer a single byte via SPI (full duplex)
 *
 * IMPORTANT: Includes timeout to prevent infinite loops.
 * This was a critical lesson from the RGB DMA issue during PlatformIO migration.
 */
uint8_t hal_spi_transfer_byte(uint8_t tx_data)
{
    uint32_t timeout;

    // Wait for TX buffer empty (with timeout)
    timeout = SPI_TIMEOUT_COUNT;
    while (SPI_I2S_GetFlagStatus(SPI2, SPI_I2S_FLAG_TXE) == RESET && timeout--)
    {
        if (timeout == 0)
        {
            return 0xFF;  // Timeout error
        }
    }

    // Send data
    SPI_I2S_SendData(SPI2, tx_data);

    // Wait for RX buffer not empty (with timeout)
    timeout = SPI_TIMEOUT_COUNT;
    while (SPI_I2S_GetFlagStatus(SPI2, SPI_I2S_FLAG_RXNE) == RESET && timeout--)
    {
        if (timeout == 0)
        {
            return 0xFF;  // Timeout error
        }
    }

    // Read received data
    return (uint8_t)SPI_I2S_ReceiveData(SPI2);
}

/**
 * @brief Transfer multiple bytes via SPI (full duplex)
 */
void hal_spi_transfer_bytes(const uint8_t *tx_data, uint8_t *rx_data, uint16_t length)
{
    for (uint16_t i = 0; i < length; i++)
    {
        uint8_t tx_byte = (tx_data != NULL) ? tx_data[i] : 0x00;
        uint8_t rx_byte = hal_spi_transfer_byte(tx_byte);

        if (rx_data != NULL)
        {
            rx_data[i] = rx_byte;
        }
    }
}

/**
 * @brief Write a single byte to SPI (TX only, discard RX)
 */
void hal_spi_write_byte(uint8_t data)
{
    hal_spi_transfer_byte(data);
}

/**
 * @brief Write multiple bytes to SPI (TX only, discard RX)
 */
void hal_spi_write_bytes(const uint8_t *data, uint16_t length)
{
    hal_spi_transfer_bytes(data, NULL, length);
}

/**
 * @brief Read a single byte from SPI (send 0x00, capture RX)
 */
uint8_t hal_spi_read_byte(void)
{
    return hal_spi_transfer_byte(0x00);
}

/**
 * @brief Read multiple bytes from SPI (send 0x00, capture RX)
 */
void hal_spi_read_bytes(uint8_t *data, uint16_t length)
{
    hal_spi_transfer_bytes(NULL, data, length);
}

/**
 * @brief Set SPI clock speed
 */
int hal_spi_set_speed(uint16_t prescaler)
{
    uint16_t spi_prescaler;

    // Convert prescaler value to SPI register value
    switch (prescaler)
    {
        case 2:   spi_prescaler = SPI_BaudRatePrescaler_2; break;
        case 4:   spi_prescaler = SPI_BaudRatePrescaler_4; break;
        case 8:   spi_prescaler = SPI_BaudRatePrescaler_8; break;
        case 16:  spi_prescaler = SPI_BaudRatePrescaler_16; break;
        case 32:  spi_prescaler = SPI_BaudRatePrescaler_32; break;
        case 64:  spi_prescaler = SPI_BaudRatePrescaler_64; break;
        case 128: spi_prescaler = SPI_BaudRatePrescaler_128; break;
        case 256: spi_prescaler = SPI_BaudRatePrescaler_256; break;
        default:
            return -1;  // Invalid prescaler
    }

    // Disable SPI before changing configuration
    SPI_Cmd(SPI2, DISABLE);

    // Modify prescaler bits (CR1 bits 5:3)
    uint16_t cr1 = SPI2->CR1;
    cr1 &= ~(0x38);  // Clear bits 5:3
    cr1 |= spi_prescaler;
    SPI2->CR1 = cr1;

    // Re-enable SPI
    SPI_Cmd(SPI2, ENABLE);

    return 0;
}
