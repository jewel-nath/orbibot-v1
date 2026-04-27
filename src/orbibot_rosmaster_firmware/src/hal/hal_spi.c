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
 * Hardware:  SPI2 on APB1 (36 MHz max)
 *   PB12  CS   — GPIO output, manual control
 *   PB13  SCK  — AF push-pull
 *   PB14  MISO — input floating
 *   PB15  MOSI — AF push-pull
 *
 * SPI mode: Mode 0 (CPOL=Low, CPHA=1Edge)
 *   ICM-20948 supports Mode 0 and Mode 3. Mode 0 is used here.
 *   If WHO_AM_I keeps returning 0xFF/0x00, try Mode 3:
 *     SPI_CPOL = SPI_CPOL_High, SPI_CPHA = SPI_CPHA_2Edge
 *
 * Clock: APB1 (36 MHz) / prescaler 8 = 4.5 MHz
 *   ICM-20948 register access limit: 7 MHz — 4.5 MHz has safe margin.
 *   If communication is unreliable, increase prescaler to 16 (2.25 MHz).
 */
int hal_spi_init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    SPI_InitTypeDef SPI_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_SPI2, ENABLE);

    /* SCK (PB13) and MOSI (PB15): alternate function push-pull */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_13 | GPIO_Pin_15;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* MISO (PB14): input floating */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_14;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* CS (PB12): GPIO output push-pull, deasserted high at boot */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_12;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &GPIO_InitStructure);
    GPIO_SetBits(GPIOB, GPIO_Pin_12);   /* CS idle = high */

    SPI_InitStructure.SPI_Direction        = SPI_Direction_2Lines_FullDuplex;
    SPI_InitStructure.SPI_Mode             = SPI_Mode_Master;
    SPI_InitStructure.SPI_DataSize         = SPI_DataSize_8b;
    SPI_InitStructure.SPI_CPOL             = SPI_CPOL_Low;          /* Mode 0: clock idle low  */
    SPI_InitStructure.SPI_CPHA             = SPI_CPHA_1Edge;         /* Mode 0: sample on rise  */
    SPI_InitStructure.SPI_NSS              = SPI_NSS_Soft;           /* CS controlled by GPIO   */
    SPI_InitStructure.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_8; /* 36MHz/8 = 4.5MHz       */
    SPI_InitStructure.SPI_FirstBit         = SPI_FirstBit_MSB;
    SPI_InitStructure.SPI_CRCPolynomial    = 7;
    SPI_Init(SPI2, &SPI_InitStructure);

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
