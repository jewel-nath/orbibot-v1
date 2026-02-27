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
 * @brief Send a null-terminated string via USART
 * @param str Pointer to null-terminated string
 */
void hal_usart_send_string(const char *str);

/**
 * @brief Check if data is available in RX buffer
 * @return Number of bytes available
 */
uint16_t hal_usart_available(void);

/**
 * @brief Read a single byte from RX buffer
 * @param data Pointer to store received byte
 * @return 1 if byte read successfully, 0 if buffer empty
 */
uint8_t hal_usart_read_byte(uint8_t *data);

/**
 * @brief Read multiple bytes from RX buffer
 * @param data Pointer to buffer for received data
 * @param max_length Maximum number of bytes to read
 * @return Number of bytes actually read
 */
uint16_t hal_usart_read_bytes(uint8_t *data, uint16_t max_length);

/**
 * @brief Flush TX buffer (wait for all data to be sent)
 */
void hal_usart_flush_tx(void);

/**
 * @brief Clear RX buffer
 */
void hal_usart_flush_rx(void);

/**
 * @brief Get USART error status
 * @return Error flags (0 = no errors)
 */
uint32_t hal_usart_get_errors(void);

#endif // HAL_USART_H
