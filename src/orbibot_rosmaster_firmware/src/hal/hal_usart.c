/**
 * @file hal_usart.c
 * @brief USART Hardware Abstraction Layer Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Features DMA-based TX for non-blocking serial transmission.
 * DMA approach enables high-speed data rates (25Hz per data type).
 */

#include "hal_usart.h"
#include "protocol.h"
#include "stm32f10x.h"
#include "stm32f10x_dma.h"
#include "orbibot_config.h"
#include <string.h>

// Enable DMA for USART1 TX
#define ENABLE_USART1_DMA       1

// DMA TX buffer size (must be large enough for largest packet ~30 bytes)
#define USART_DMA_TX_BUFFER_SIZE    128

#if ENABLE_USART1_DMA
// DMA TX buffer
static uint8_t dma_tx_buffer[USART_DMA_TX_BUFFER_SIZE];
#endif

// Error tracking (accumulated in ISR, readable via hal_usart_get_errors)
static volatile uint32_t usart_errors = 0;

#if ENABLE_USART1_DMA
/**
 * @brief Initialize DMA for USART1 TX
 *
 * Uses DMA1 Channel4 which is the hardware-mapped channel for USART1_TX.
 * This enables non-blocking serial transmission for high data rates.
 */
static void usart1_dma_init(void)
{
    DMA_InitTypeDef DMA_InitStructure;

    // Enable DMA1 clock
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);

    // Configure DMA1 Channel4 for USART1 TX
    DMA_DeInit(DMA1_Channel4);

    DMA_InitStructure.DMA_PeripheralBaseAddr = (uint32_t)(&USART1->DR);
    DMA_InitStructure.DMA_MemoryBaseAddr = (uint32_t)dma_tx_buffer;
    DMA_InitStructure.DMA_DIR = DMA_DIR_PeripheralDST;
    DMA_InitStructure.DMA_BufferSize = 0;
    DMA_InitStructure.DMA_PeripheralInc = DMA_PeripheralInc_Disable;
    DMA_InitStructure.DMA_MemoryInc = DMA_MemoryInc_Enable;
    DMA_InitStructure.DMA_PeripheralDataSize = DMA_PeripheralDataSize_Byte;
    DMA_InitStructure.DMA_MemoryDataSize = DMA_MemoryDataSize_Byte;
    DMA_InitStructure.DMA_Mode = DMA_Mode_Normal;
    DMA_InitStructure.DMA_Priority = DMA_Priority_High;
    DMA_InitStructure.DMA_M2M = DMA_M2M_Disable;

    DMA_Init(DMA1_Channel4, &DMA_InitStructure);

    // Enable USART1 DMA TX request
    USART_DMACmd(USART1, USART_DMAReq_Tx, ENABLE);

}
#endif

/**
 * @brief Initialize USART1 for serial communication
 *
 * Configuration:
 * - USART1: PA9 (TX), PA10 (RX)
 * - 8 data bits, 1 stop bit, no parity
 * - Hardware flow control disabled
 * - RX interrupt forwards each byte to protocol_receive_byte()
 * - DMA enabled for TX (non-blocking transmission)
 */
int hal_usart_init(uint32_t baudrate)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    USART_InitTypeDef USART_InitStructure;
    NVIC_InitTypeDef NVIC_InitStructure;

    // Enable clocks for GPIOA and USART1
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_USART1, ENABLE);

    // Configure PA9 (TX) as alternate function push-pull
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_9;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // Configure PA10 (RX) as input floating
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // Configure USART1
    USART_InitStructure.USART_BaudRate = baudrate;
    USART_InitStructure.USART_WordLength = USART_WordLength_8b;
    USART_InitStructure.USART_StopBits = USART_StopBits_1;
    USART_InitStructure.USART_Parity = USART_Parity_No;
    USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    USART_InitStructure.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART1, &USART_InitStructure);

    // Enable USART1 RX interrupt
    USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);

    // Configure NVIC for USART1 interrupt
    // NOTE: With NVIC_PriorityGroup_2, valid preemption priorities are 0-3 only!
    NVIC_InitStructure.NVIC_IRQChannel = USART1_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 1;  // High priority for RX
    NVIC_InitStructure.NVIC_IRQChannelSubPriority = 3;
    NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&NVIC_InitStructure);

    // Enable USART1
    USART_Cmd(USART1, ENABLE);

    // Clear TC flag to prevent first byte loss after reset
    USART_ClearFlag(USART1, USART_FLAG_TC);

#if ENABLE_USART1_DMA
    // Initialize DMA for TX
    usart1_dma_init();
#endif

    usart_errors = 0;

    return 0;
}

/**
 * @brief Send a single byte via USART
 */
void hal_usart_send_byte(uint8_t data)
{
    // Wait for TX buffer to be empty
    while (USART_GetFlagStatus(USART1, USART_FLAG_TXE) == RESET);

    // Send data
    USART_SendData(USART1, data);
}

/**
 * @brief Send multiple bytes via USART using DMA (non-blocking)
 *
 * With DMA enabled, this function:
 * 1. Waits for any previous DMA transfer to complete
 * 2. Copies data to DMA buffer
 * 3. Starts DMA transfer and returns immediately
 *
 * This is the key optimization that allows 25Hz data rates.
 */
void hal_usart_send_bytes(const uint8_t *data, uint16_t length)
{
    if (length == 0) return;

#if ENABLE_USART1_DMA
    // Wait for previous DMA transfer to complete (timeout ~2ms at 72MHz)
    uint32_t timeout = 144000;
    while (DMA_GetCurrDataCounter(DMA1_Channel4) != 0)
    {
        if (--timeout == 0)
        {
            // DMA stalled — disable channel and continue to recover
            DMA_Cmd(DMA1_Channel4, DISABLE);
            break;
        }
    }

    // Limit length to buffer size
    if (length > USART_DMA_TX_BUFFER_SIZE)
    {
        length = USART_DMA_TX_BUFFER_SIZE;
    }

    // Copy data to DMA buffer
    memcpy(dma_tx_buffer, data, length);

    // Start DMA transfer
    DMA_Cmd(DMA1_Channel4, DISABLE);
    DMA1_Channel4->CNDTR = length;
    DMA_Cmd(DMA1_Channel4, ENABLE);

#else
    // Blocking fallback (original implementation)
    for (uint16_t i = 0; i < length; i++)
    {
        hal_usart_send_byte(data[i]);
    }
#endif
}

/**
 * @brief Flush TX buffer (wait for all data to be sent)
 */
void hal_usart_flush_tx(void)
{
#if ENABLE_USART1_DMA
    uint32_t timeout = 144000;
    while (DMA_GetCurrDataCounter(DMA1_Channel4) != 0)
    {
        if (--timeout == 0)
        {
            DMA_Cmd(DMA1_Channel4, DISABLE);
            break;
        }
    }
#endif
    uint32_t tc_timeout = 72000;
    while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET)
    {
        if (--tc_timeout == 0) break;
    }
}

/**
 * @brief Get USART error status
 */
uint32_t hal_usart_get_errors(void)
{
    return usart_errors;
}

/**
 * @brief USART1 interrupt handler
 *
 * This interrupt is triggered when:
 * - Data received (RXNE flag)
 * - Transmission complete (TC flag)
 * - Errors (overrun, framing, noise, parity)
 */
void USART1_IRQHandler(void)
{
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET)
    {
        uint8_t data = USART_ReceiveData(USART1);
        protocol_receive_byte(data);
    }

    // Clear hardware errors by reading DR (STM32 requirement)
    if (USART_GetFlagStatus(USART1, USART_FLAG_ORE) != RESET)
    {
        (void)USART_ReceiveData(USART1);
        usart_errors |= (1 << 1);
    }
    if (USART_GetFlagStatus(USART1, USART_FLAG_FE) != RESET)
    {
        (void)USART_ReceiveData(USART1);
        usart_errors |= (1 << 2);
    }
    if (USART_GetFlagStatus(USART1, USART_FLAG_NE) != RESET)
    {
        (void)USART_ReceiveData(USART1);
        usart_errors |= (1 << 3);
    }
}

/**
 * @brief Printf redirection for GCC newlib
 *
 * This is required for printf() to work with GCC toolchain.
 * GCC newlib uses _write() syscall instead of fputc().
 *
 * IMPORTANT: This was a critical fix discovered during PlatformIO migration.
 * Keil uses fputc(), but GCC requires _write() for printf support.
 */
int _write(int file, char *ptr, int len)
{
    (void)file;  // Unused parameter

    for (int i = 0; i < len; i++)
    {
        hal_usart_send_byte(*ptr++);
    }

    return len;
}

/**
 * @brief Fallback fputc for compatibility
 *
 * Some libraries may still call fputc() directly.
 */
int fputc(int ch, FILE *f)
{
    (void)f;  // Unused parameter
    hal_usart_send_byte((uint8_t)ch);
    return ch;
}
