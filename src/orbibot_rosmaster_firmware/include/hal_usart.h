/**
 * @file hal_usart.h
 * @brief USART Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Provides USART communication interface for:
 * - Debug output (printf redirection)
 * - Serial communication with ROS2 host
 * - Command reception from host computer
 *
 * Hardware: USART1 on PA9 (TX) and PA10 (RX)
 * Baud rate: Configurable (default 115200)
 */

#ifndef HAL_USART_H
#define HAL_USART_H

#include <stdint.h>
#include <stdio.h>

/**
 * @brief Initialize USART1 for serial communication
 * @param baudrate Baud rate (e.g., 115200)
 * @return 0 on success, -1 on failure
 */
int hal_usart_init(uint32_t baudrate);

/**
 * @brief Send a single byte via USART
 * @param data Byte to send
 */
void hal_usart_send_byte(uint8_t data);

/**
 * @brief Send multiple bytes via USART
 * @param data Pointer to data buffer
 * @param length Number of bytes to send
 */
void hal_usart_send_bytes(const uint8_t *data, uint16_t length);

/**
 * @brief Flush TX buffer (wait for all data to be sent)
 */
void hal_usart_flush_tx(void);

/**
 * @brief Get USART error status
 * @return Error flags (0 = no errors). Bit 1: overrun, Bit 2: framing, Bit 3: noise.
 */
uint32_t hal_usart_get_errors(void);

#endif // HAL_USART_H
