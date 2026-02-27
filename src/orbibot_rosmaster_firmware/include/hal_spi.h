/**
 * @file hal_spi.h
 * @brief SPI Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Provides SPI communication interface for ICM-20948 IMU sensor.
 *
 * Hardware: SPI2 on PB13 (SCK), PB14 (MISO), PB15 (MOSI), PB12 (CS)
 * Clock: 8MHz SPI clock (APB1 / 4 = 36MHz / 4 = 9MHz, closest to 8MHz)
 * Mode: Mode 0 or Mode 3 (CPOL=0/1, CPHA=0/1) - ICM-20948 supports both
 */

#ifndef HAL_SPI_H
#define HAL_SPI_H

#include <stdint.h>

/**
 * @brief Initialize SPI2 for IMU communication
 * @return 0 on success, -1 on failure
 */
int hal_spi_init(void);

/**
 * @brief Select SPI device (assert CS low)
 */
void hal_spi_select(void);

/**
 * @brief Deselect SPI device (release CS high)
 */
void hal_spi_deselect(void);

/**
 * @brief Transfer a single byte via SPI (full duplex)
 * @param tx_data Byte to transmit
 * @return Byte received during transfer
 */
uint8_t hal_spi_transfer_byte(uint8_t tx_data);

/**
 * @brief Transfer multiple bytes via SPI (full duplex)
 * @param tx_data Pointer to transmit buffer (NULL to send 0x00)
 * @param rx_data Pointer to receive buffer (NULL to discard)
 * @param length Number of bytes to transfer
 */
void hal_spi_transfer_bytes(const uint8_t *tx_data, uint8_t *rx_data, uint16_t length);

/**
 * @brief Write a single byte to SPI (TX only, discard RX)
 * @param data Byte to write
 */
void hal_spi_write_byte(uint8_t data);

/**
 * @brief Write multiple bytes to SPI (TX only, discard RX)
 * @param data Pointer to data buffer
 * @param length Number of bytes to write
 */
void hal_spi_write_bytes(const uint8_t *data, uint16_t length);

/**
 * @brief Read a single byte from SPI (send 0x00, capture RX)
 * @return Byte received
 */
uint8_t hal_spi_read_byte(void);

/**
 * @brief Read multiple bytes from SPI (send 0x00, capture RX)
 * @param data Pointer to buffer for received data
 * @param length Number of bytes to read
 */
void hal_spi_read_bytes(uint8_t *data, uint16_t length);

/**
 * @brief Set SPI clock speed
 * @param prescaler SPI prescaler (2, 4, 8, 16, 32, 64, 128, 256)
 * @return 0 on success, -1 on invalid prescaler
 */
int hal_spi_set_speed(uint16_t prescaler);

#endif // HAL_SPI_H
