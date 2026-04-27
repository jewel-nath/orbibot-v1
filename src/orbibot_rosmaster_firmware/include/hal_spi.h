/**
 * @file hal_spi.h
 * @brief SPI Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * SPI2 on PB13 (SCK), PB14 (MISO), PB15 (MOSI), PB12 (CS).
 * Used exclusively by imu_driver for ICM-20948 access at 4.5 MHz, Mode 0.
 */

#ifndef HAL_SPI_H
#define HAL_SPI_H

#include <stdint.h>

int hal_spi_init(void);
void hal_spi_select(void);
void hal_spi_deselect(void);

/** Transfer one byte full-duplex. Returns 0xFF on TXE/RXNE timeout. */
uint8_t hal_spi_transfer_byte(uint8_t tx_data);

/** Transfer a buffer full-duplex; tx or rx may be NULL (discard that direction). */
void hal_spi_transfer_bytes(const uint8_t *tx_data, uint8_t *rx_data, uint16_t length);

/** TX-only convenience wrappers; return-value is discarded. */
void hal_spi_write_byte(uint8_t data);

/** RX-only convenience wrappers; TX bytes are 0x00. */
uint8_t hal_spi_read_byte(void);
void hal_spi_read_bytes(uint8_t *data, uint16_t length);

#endif // HAL_SPI_H
