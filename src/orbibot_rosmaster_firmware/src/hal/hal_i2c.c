/**
 * @file hal_i2c.c
 * @brief I2C Hardware Abstraction Layer (Software I2C for OLED)
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Software I2C implementation for SSD1306 OLED display.
 * Pin assignments from orbibot_config.h (PA2/PA3 on ROSMaster V3.0).
 */

#include "hal_i2c.h"
#include "stm32f10x.h"
#include "orbibot_config.h"

// Use pin definitions from orbibot_config.h
#define I2C_SCL_PIN     OLED_SCL_PIN
#define I2C_SDA_PIN     OLED_SDA_PIN
#define I2C_SCL_PORT    OLED_SCL_PORT
#define I2C_SDA_PORT    OLED_SDA_PORT

// I2C pin control macros
#define I2C_SCL_HIGH()  GPIO_SetBits(I2C_SCL_PORT, I2C_SCL_PIN)
#define I2C_SCL_LOW()   GPIO_ResetBits(I2C_SCL_PORT, I2C_SCL_PIN)
#define I2C_SDA_HIGH()  GPIO_SetBits(I2C_SDA_PORT, I2C_SDA_PIN)
#define I2C_SDA_LOW()   GPIO_ResetBits(I2C_SDA_PORT, I2C_SDA_PIN)
#define I2C_SDA_READ()  GPIO_ReadInputDataBit(I2C_SDA_PORT, I2C_SDA_PIN)

// Timing delay (at 72MHz, ~1us per iteration)
static void i2c_delay(void)
{
    volatile uint8_t i = 10;
    while (i--);
}

// Set SDA as output
static void sda_out(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Pin = I2C_SDA_PIN;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(I2C_SDA_PORT, &GPIO_InitStructure);
}

// Set SDA as input
static void sda_in(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Pin = I2C_SDA_PIN;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(I2C_SDA_PORT, &GPIO_InitStructure);
}

// I2C start condition
static void i2c_start(void)
{
    sda_out();
    I2C_SDA_HIGH();
    I2C_SCL_HIGH();
    i2c_delay();
    I2C_SDA_LOW();
    i2c_delay();
    I2C_SCL_LOW();
}

// I2C stop condition
static void i2c_stop(void)
{
    sda_out();
    I2C_SCL_LOW();
    I2C_SDA_LOW();
    i2c_delay();
    I2C_SCL_HIGH();
    i2c_delay();
    I2C_SDA_HIGH();
    i2c_delay();
}

// Wait for ACK (return 1 if ACK received, 0 if NACK)
static uint8_t i2c_wait_ack(void)
{
    uint8_t timeout = 0;
    
    sda_in();
    I2C_SDA_HIGH();
    i2c_delay();
    I2C_SCL_HIGH();
    i2c_delay();
    
    while (I2C_SDA_READ())
    {
        timeout++;
        if (timeout > 250)
        {
            i2c_stop();
            return 0;
        }
    }
    
    I2C_SCL_LOW();
    return 1;
}

// Send ACK
static void i2c_ack(void)
{
    I2C_SCL_LOW();
    sda_out();
    I2C_SDA_LOW();
    i2c_delay();
    I2C_SCL_HIGH();
    i2c_delay();
    I2C_SCL_LOW();
}

// Send NACK
static void i2c_nack(void)
{
    I2C_SCL_LOW();
    sda_out();
    I2C_SDA_HIGH();
    i2c_delay();
    I2C_SCL_HIGH();
    i2c_delay();
    I2C_SCL_LOW();
}

// Send one byte
static void i2c_send_byte(uint8_t data)
{
    uint8_t i;
    
    sda_out();
    I2C_SCL_LOW();
    
    for (i = 0; i < 8; i++)
    {
        if (data & 0x80)
            I2C_SDA_HIGH();
        else
            I2C_SDA_LOW();
        
        data <<= 1;
        i2c_delay();
        I2C_SCL_HIGH();
        i2c_delay();
        I2C_SCL_LOW();
        i2c_delay();
    }
}

// Read one byte
static uint8_t i2c_read_byte(uint8_t ack)
{
    uint8_t i, data = 0;
    
    sda_in();
    
    for (i = 0; i < 8; i++)
    {
        I2C_SCL_LOW();
        i2c_delay();
        I2C_SCL_HIGH();
        data <<= 1;
        
        if (I2C_SDA_READ())
            data++;
        
        i2c_delay();
    }
    
    if (ack)
        i2c_ack();
    else
        i2c_nack();
    
    return data;
}

/**
 * @brief Initialize I2C peripheral (software I2C)
 * @return 0 on success, -1 on failure
 */
int hal_i2c_init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    // Enable GPIO clocks for OLED pins (PA2/PA3 on GPIOA)
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);

    // Configure SCL pin as output
    GPIO_InitStructure.GPIO_Pin = I2C_SCL_PIN;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(I2C_SCL_PORT, &GPIO_InitStructure);

    // Configure SDA pin as output (switches to input when reading)
    GPIO_InitStructure.GPIO_Pin = I2C_SDA_PIN;
    GPIO_Init(I2C_SDA_PORT, &GPIO_InitStructure);
    
    // Set both pins high (idle state)
    I2C_SCL_HIGH();
    I2C_SDA_HIGH();
    
    return 0;
}

/**
 * @brief Write data to I2C device
 * @param address I2C device address (7-bit, will be shifted)
 * @param reg Register address or command byte
 * @param count Number of bytes to write
 * @param data Pointer to data buffer
 * @return 0 on success, -1 on failure
 */
int i2cWrite(uint8_t address, uint8_t reg, uint16_t count, uint8_t *data)
{
    uint16_t i;
    
    i2c_start();
    
    // Send device address + write bit
    i2c_send_byte((address << 1) | 0);
    if (!i2c_wait_ack())
        return -1;
    
    // Send register/command byte
    i2c_send_byte(reg);
    if (!i2c_wait_ack())
        return -1;
    
    // Send data bytes
    for (i = 0; i < count; i++)
    {
        i2c_send_byte(data[i]);
        if (!i2c_wait_ack())
            return -1;
    }
    
    i2c_stop();
    return 0;
}

/**
 * @brief Read data from I2C device
 * @param address I2C device address (7-bit, will be shifted)
 * @param reg Register address
 * @param count Number of bytes to read
 * @param data Pointer to data buffer
 * @return 0 on success, -1 on failure
 */
int i2cRead(uint8_t address, uint8_t reg, uint16_t count, uint8_t *data)
{
    uint16_t i;
    
    i2c_start();
    
    // Send device address + write bit
    i2c_send_byte((address << 1) | 0);
    if (!i2c_wait_ack())
        return -1;
    
    // Send register address
    i2c_send_byte(reg);
    if (!i2c_wait_ack())
        return -1;
    
    // Repeated start
    i2c_start();
    
    // Send device address + read bit
    i2c_send_byte((address << 1) | 1);
    if (!i2c_wait_ack())
        return -1;
    
    // Read data bytes
    for (i = 0; i < count; i++)
    {
        data[i] = i2c_read_byte(i < (count - 1));
    }
    
    i2c_stop();
    return 0;
}
