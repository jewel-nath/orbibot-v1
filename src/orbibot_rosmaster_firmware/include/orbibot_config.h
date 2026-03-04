/**
 * @file orbibot_config.h
 * @brief OrbiBot robot configuration parameters
 * @author Jewel Nath
 * @date 2025-11-27
 *
 * This file contains all robot-specific parameters for OrbiBot:
 * - Physical dimensions (wheel size, wheelbase, track width)
 * - Motor specifications (type, gear ratio, encoder resolution)
 * - Safety limits (max velocity, battery thresholds)
 * - Control parameters (PID gains, update rates)
 */

#ifndef ORBIBOT_CONFIG_H
#define ORBIBOT_CONFIG_H

#include <stdint.h>

/* ========================================================================
 * MATHEMATICAL CONSTANTS
 * ======================================================================== */

#define PI_F    3.14159265f     // Single authoritative pi constant for all firmware

/* ========================================================================
 * PHYSICAL PARAMETERS
 * ======================================================================== */

/**
 * Wheel Configuration
 * OrbiBot uses 100mm mecanum wheels (50mm radius)
 */
#define WHEEL_RADIUS_M              0.050f      // 50mm wheel radius
#define WHEEL_DIAMETER_M            0.100f      // 100mm wheel diameter
#define WHEEL_CIRCUMFERENCE_M       (PI_F * WHEEL_DIAMETER_M)  // Derived from diameter

/**
 * Robot Dimensions
 * Measurements from wheel contact points
 */
#define WHEEL_BASE_M                0.260f      // 260mm front-to-rear distance
#define TRACK_WIDTH_M               0.360f      // 360mm left-to-right distance

/**
 * Mecanum Wheel Layout (ABBA pattern)
 * A-type: Rollers at +45° (top-left to bottom-right)
 * B-type: Rollers at -45° (top-right to bottom-left)
 */
#define MECANUM_LAYOUT_FRONT_LEFT   'A'
#define MECANUM_LAYOUT_FRONT_RIGHT  'B'
#define MECANUM_LAYOUT_BACK_LEFT    'B'
#define MECANUM_LAYOUT_BACK_RIGHT   'A'

/* ========================================================================
 * MOTOR SPECIFICATIONS
 * ======================================================================== */

/**
 * Motor: JGB37-520
 * - No-load speed: 333 RPM
 * - Gear ratio: 1:30
 * - Encoder: Hall effect quadrature
 * - Resolution: 1320 pulses per revolution (after gearbox)
 */
#define MOTOR_TYPE                  "JGB37-520"
#define MOTOR_GEAR_RATIO            30.0f
#define MOTOR_RPM_MAX               333
#define ENCODER_PPR                 1320        // Counts per wheel revolution (11 PPR × 30 gear × 4 quadrature)
#define ENCODER_EDGES_PER_REV       ENCODER_PPR // Same as ENCODER_PPR (quadrature already included)

/**
 * Motor PWM Configuration
 * - Frequency: 20kHz (ultrasonic, silent operation)
 * - Resolution: 16-bit timer (0-65535)
 */
#define MOTOR_PWM_FREQUENCY_HZ      20000
#define MOTOR_PWM_PERIOD            3600        // For 72MHz / 20kHz
#define MOTOR_PWM_MAX_DUTY          0.95f       // 95% max (prevent saturation)

/* ========================================================================
 * VELOCITY LIMITS
 * ======================================================================== */

/**
 * Safety Velocity Limits
 * These prevent damage to motors and ensure safe operation
 */
#define MAX_LINEAR_VELOCITY_MPS     1.0f        // 1.0 m/s linear speed
#define MAX_ANGULAR_VELOCITY_RPS    2.0f        // 2.0 rad/s rotation speed
#define MAX_WHEEL_RPM               (MOTOR_RPM_MAX * 0.9f)  // 90% of max

/**
 * Acceleration Limits (for smooth motion)
 */
#define MAX_LINEAR_ACCEL_MPS2       2.0f        // 2.0 m/s² acceleration
#define MAX_ANGULAR_ACCEL_RPS2      4.0f        // 4.0 rad/s² angular accel

/**
 * Velocity Ramp (asymmetric: instant accel, gradual decel)
 * Applied per-wheel in the control loop at 100Hz.
 * Ramp rate = MOTOR_SPEED_RAMP_MMS * 100Hz = 1000 mm/s² deceleration.
 */
#define MOTOR_SPEED_RAMP_MMS        10.0f       // mm/s per 100Hz tick

/* ========================================================================
 * BATTERY CONFIGURATION
 * ======================================================================== */

/**
 * Battery: 4S LiFePO4 (12.8V nominal, 14.6V fully charged)
 * Chemistry: Lithium Iron Phosphate (LiFePO4)
 * Capacity: 15Ah (15,500mAh)
 * - Nominal: 12.8V (3.2V per cell)
 * - Fully charged: 14.6V (3.65V per cell)
 * - Low voltage: 11.6V (2.9V per cell - ~20% remaining)
 * - Critical: 10.0V (2.5V per cell - BMS cutoff, stop immediately)
 */
#define BATTERY_CELLS               4
#define BATTERY_VOLTAGE_NOMINAL     12.8f       // Volts
#define BATTERY_VOLTAGE_FULL        14.6f       // Volts
#define BATTERY_VOLTAGE_LOW         11.0f       // Warning threshold (~20%)
#define BATTERY_VOLTAGE_CRITICAL    10.5f       // Emergency stop threshold (matches ROS2 config)

/**
 * ADC Configuration for Battery Monitoring
 * Voltage divider: R1=10kΩ, R2=3.3kΩ (ratio ~4.03)
 * ROSMaster V3.0 board standard voltage divider configuration
 */
#define BATTERY_ADC_RATIO           4.03f       // Voltage divider ratio
#define BATTERY_MONITOR_RATE_HZ     1.0f        // Check every 1 second

/* ========================================================================
 * CONTROL PARAMETERS
 * ======================================================================== */

/**
 * Motor PID Controller — Multi-Level Gains
 * 3 gain levels with linear interpolation between speed thresholds.
 * Tuned for JGB37-520 motors with AM2857 drivers.
 *
 * Level 0 (low speed):   High Kp for crisp start, low Ki to avoid overshoot
 * Level 1 (mid speed):   Balanced — matches original single-level gains
 * Level 2 (high speed):  Lower Kp to reduce oscillation at speed
 */
#define PID_NUM_LEVELS              3

// Speed thresholds (mm/s) — boundaries between PID gain levels
#define PID_SPEED_THRESHOLD_0       50.0f       // Below this: use Level 0
#define PID_SPEED_THRESHOLD_1       200.0f      // Between 0-1: interpolate
#define PID_SPEED_THRESHOLD_2       500.0f      // Above this: use Level 2

// Level 0: Low speed (0–50 mm/s)
#define PID_KP_L0                   1.2f
#define PID_KI_L0                   0.04f
#define PID_KD_L0                   0.6f

// Level 1: Medium speed (50–200 mm/s)
#define PID_KP_L1                   0.8f
#define PID_KI_L1                   0.06f
#define PID_KD_L1                   0.5f

// Level 2: High speed (200–500+ mm/s)
#define PID_KP_L2                   0.5f
#define PID_KI_L2                   0.08f
#define PID_KD_L2                   0.4f

// Legacy single-level defaults (backward compat for control_set_motor_pid)
#define PID_KP                      PID_KP_L1
#define PID_KI                      PID_KI_L1
#define PID_KD                      PID_KD_L1

#define PID_MAX_INTEGRAL            4000.0f     // Anti-windup limit
#define PID_OUTPUT_MIN              -1.0f       // Minimum output (reverse)
#define PID_OUTPUT_MAX              1.0f        // Maximum output (forward)

/**
 * Yaw PID Controller Gains (for heading drift compensation)
 * Corrects heading drift during straight-line motion using IMU feedback
 */
#define YAW_PID_KP                  0.4f        // Proportional gain
#define YAW_PID_KI                  0.0f        // Integral gain
#define YAW_PID_KD                  0.1f        // Derivative gain
#define YAW_PID_MAX_OUTPUT          500.0f      // Max correction offset
#define YAW_ENABLE_THRESHOLD        0.05f       // Min speed (m/s) to enable yaw correction
#define MOTOR_MAX_PULSE             3600        // Max PWM pulse
#define MOTOR_IGNORE_PULSE          1600        // Deadzone pulse for AM2857 drivers

/**
 * Control Loop Rates
 */
#define CONTROL_LOOP_RATE_HZ        100         // Motor PID update rate (odometry also @ 100Hz)
#define IMU_UPDATE_RATE_HZ          50          // IMU data acquisition rate
#define DIAGNOSTICS_RATE_HZ         10          // Status monitoring rate

/* ========================================================================
 * SAFETY PARAMETERS
 * ======================================================================== */

/**
 * Command Timeout
 * If no velocity command received for this duration, motors stop
 */
#define COMMAND_TIMEOUT_MS          2000        // 2 seconds

/**
 * Watchdog Timer (IWDG - Independent Watchdog)
 * Resets MCU if firmware hangs or stops responding
 *
 * IMPORTANT: For production deployment, set ENABLE_WATCHDOG to 1
 * The watchdog is fed in task_monitoring every 1 second.
 * Timeout is 5 seconds, giving margin for FreeRTOS task scheduling.
 */
#define ENABLE_WATCHDOG             1           // 0=dev (debug easier), 1=production
#define WATCHDOG_TIMEOUT_MS         5000        // 5 seconds

/* ========================================================================
 * IMU CONFIGURATION (ICM-20948)
 * ======================================================================== */

/**
 * IMU: TDK InvenSense ICM-20948
 * - 9-axis: 3-axis gyro + 3-axis accel + 3-axis magnetometer
 * - Interface: SPI2 (faster than I2C)
 * - Update rate: 50Hz (matches odometry rate)
 */
#define IMU_TYPE                    "ICM20948"
#define IMU_INTERFACE               "SPI2"
// IMU_UPDATE_RATE_HZ defined in Control Parameters section above

/**
 * IMU Sensor Ranges
 */
#define IMU_GYRO_RANGE_DPS          2000        // ±2000 °/s
#define IMU_ACCEL_RANGE_G           16          // ±16g
#define IMU_MAG_RANGE_UT            4900        // ±4900 μT

/**
 * IMU Calibration (set these after calibration)
 */
#define IMU_GYRO_BIAS_X             0.0f
#define IMU_GYRO_BIAS_Y             0.0f
#define IMU_GYRO_BIAS_Z             0.0f
#define IMU_ACCEL_BIAS_X            0.0f
#define IMU_ACCEL_BIAS_Y            0.0f
#define IMU_ACCEL_BIAS_Z            0.0f

/* ========================================================================
 * COMMUNICATION PARAMETERS
 * ======================================================================== */

/**
 * Serial Communication (USART1 via Micro-USB)
 * - Connection: Raspberry Pi 5
 * - Protocol: Custom binary with checksums
 */
#define USART_BAUDRATE              115200
#define USART_PORT                  1           // USART1
#define SERIAL_RX_BUFFER_SIZE       256
#define SERIAL_TX_BUFFER_SIZE       256

/* ========================================================================
 * OPTIONAL FEATURES
 * ======================================================================== */

/**
 * OLED Display (SSD1306, 0.91", I2C 0x3C)
 * Shows robot status, battery, velocity
 */
#define ENABLE_OLED_DISPLAY         1           // Enabled for debugging

/**
 * Debug Output
 * Verbose logging via serial port
 */
#define ENABLE_DEBUG_OUTPUT         1           // Enabled during development
#define DEBUG_LEVEL                 1           // 0=None, 1=Error only (Info/Verbose interleave with protocol USART1)

/**
 * Debug Print Macros
 * Use these instead of direct printf() for conditional compilation
 */
#if ENABLE_DEBUG_OUTPUT
    #include <stdio.h>
    #if DEBUG_LEVEL >= 1
        #define DEBUG_ERROR(fmt, ...)   printf("[ERROR] " fmt, ##__VA_ARGS__)
    #else
        #define DEBUG_ERROR(fmt, ...)
    #endif
    #if DEBUG_LEVEL >= 2
        #define DEBUG_INFO(fmt, ...)    printf("[INFO] " fmt, ##__VA_ARGS__)
    #else
        #define DEBUG_INFO(fmt, ...)
    #endif
    #if DEBUG_LEVEL >= 3
        #define DEBUG_VERBOSE(fmt, ...) printf("[VERBOSE] " fmt, ##__VA_ARGS__)
    #else
        #define DEBUG_VERBOSE(fmt, ...)
    #endif
#else
    #define DEBUG_ERROR(fmt, ...)
    #define DEBUG_INFO(fmt, ...)
    #define DEBUG_VERBOSE(fmt, ...)
#endif

/* ========================================================================
 * HARDWARE PIN MAPPING (STM32F103RCT6)
 * ======================================================================== */

/**
 * Motor Driver Pins (AM2857 H-Bridge - Dual PWM per motor)
 *
 * ROSMaster V3.0 motor configuration:
 * - M1/M2 use TIM8 (CCR1-4)
 * - M3/M4 use TIM1 with GPIO_PartialRemap_TIM1 (CCR1-4)
 *
 * H-Bridge Control Logic:
 *   Forward: IN1=PWM, IN2=0
 *   Reverse: IN1=0, IN2=PWM
 *   Stop:    IN1=0, IN2=0
 *   Brake:   IN1=1, IN2=1
 */

// Motor 1 (Front-Left) - TIM8->CCR1/CCR2
#define MOTOR1_IN1_PIN              GPIO_Pin_11 // PA11 -> TIM8_CH1 (via remap)
#define MOTOR1_IN1_PORT             GPIOA
#define MOTOR1_IN2_PIN              GPIO_Pin_8  // PA8 -> TIM8_CH2 (via remap)
#define MOTOR1_IN2_PORT             GPIOA

// Motor 2 (Back-Left) - TIM8->CCR3/CCR4
#define MOTOR2_IN1_PIN              GPIO_Pin_0  // PB0 -> TIM8_CH3 (via remap)
#define MOTOR2_IN1_PORT             GPIOB
#define MOTOR2_IN2_PIN              GPIO_Pin_1  // PB1 -> TIM8_CH4 (via remap)
#define MOTOR2_IN2_PORT             GPIOB

// Motor 3 (Front-Right) - TIM1->CCR4/CCR1 (GPIO_PartialRemap_TIM1)
#define MOTOR3_IN1_PIN              GPIO_Pin_6  // PC6 -> TIM1_CH4 (remapped)
#define MOTOR3_IN1_PORT             GPIOC
#define MOTOR3_IN2_PIN              GPIO_Pin_7  // PC7 -> TIM1_CH1 (remapped)
#define MOTOR3_IN2_PORT             GPIOC

// Motor 4 (Back-Right) - TIM1->CCR2/CCR3 (complementary outputs via GPIO_PartialRemap_TIM1)
// Note: M4 uses TIM1 CH2N/CH3N complementary output mode
#define MOTOR4_IN1_PIN              GPIO_Pin_8  // PC8 -> TIM1_CH2N
#define MOTOR4_IN1_PORT             GPIOC
#define MOTOR4_IN2_PIN              GPIO_Pin_9  // PC9 -> TIM1_CH3N
#define MOTOR4_IN2_PORT             GPIOC

/**
 * Encoder Pins (Quadrature, TIM2-TIM5)
 *
 * ROSMaster V3.0 encoder configuration:
 * - TIM2 (M1): PA15/PB3 - requires GPIO_PartialRemap1_TIM2 and JTAG disable
 * - TIM3 (M4): PA6/PA7 - default pins
 * - TIM4 (M2): PB6/PB7 - default pins
 * - TIM5 (M3): PA0/PA1 - default pins
 *
 * Motor to Encoder mapping:
 * - M1 (Front-Left)  -> TIM2 (HAL3: PA15, PB3)
 * - M2 (Back-Left)   -> TIM4 (HAL4: PB6, PB7)
 * - M3 (Front-Right) -> TIM5 (HAL1: PA0, PA1)
 * - M4 (Back-Right)  -> TIM3 (HAL2: PA6, PA7)
 */

// Encoder 1 / M1 (Front-Left) - TIM2 with partial remap (JTAG disabled)
#define ENC1_A_PIN                  GPIO_Pin_15 // PA15 (TIM2_CH1 remapped)
#define ENC1_A_PORT                 GPIOA
#define ENC1_B_PIN                  GPIO_Pin_3  // PB3 (TIM2_CH2 remapped)
#define ENC1_B_PORT                 GPIOB

// Encoder 2 / M2 (Back-Left) - TIM4
#define ENC2_A_PIN                  GPIO_Pin_6  // PB6 (TIM4_CH1)
#define ENC2_A_PORT                 GPIOB
#define ENC2_B_PIN                  GPIO_Pin_7  // PB7 (TIM4_CH2)
#define ENC2_B_PORT                 GPIOB

// Encoder 3 / M3 (Front-Right) - TIM5
#define ENC3_A_PIN                  GPIO_Pin_0  // PA0 (TIM5_CH1)
#define ENC3_A_PORT                 GPIOA
#define ENC3_B_PIN                  GPIO_Pin_1  // PA1 (TIM5_CH2)
#define ENC3_B_PORT                 GPIOA

// Encoder 4 / M4 (Back-Right) - TIM3
#define ENC4_A_PIN                  GPIO_Pin_6  // PA6 (TIM3_CH1)
#define ENC4_A_PORT                 GPIOA
#define ENC4_B_PIN                  GPIO_Pin_7  // PA7 (TIM3_CH2)
#define ENC4_B_PORT                 GPIOA

/**
 * IMU Pins (ICM-20948, SPI2)
 */
#define IMU_SPI                     SPI2
#define IMU_SCK_PIN                 GPIO_Pin_13 // PB13 (SPI2_SCK)
#define IMU_MISO_PIN                GPIO_Pin_14 // PB14 (SPI2_MISO)
#define IMU_MOSI_PIN                GPIO_Pin_15 // PB15 (SPI2_MOSI)
#define IMU_CS_PIN                  GPIO_Pin_12 // PB12 (SPI2_NSS)

/**
 * Battery Monitor Pin (ADC1 Channel 14)
 * Hardware Note: Connected to PC4 on Rosmaster Expansion Board
 */
#define BATTERY_ADC_GPIO_PORT       GPIOC
#define BATTERY_ADC_PIN             GPIO_Pin_4
#define BATTERY_ADC_CHANNEL         ADC_Channel_14
#define BATTERY_ADC_GPIO_CLK        RCC_APB2Periph_GPIOC

/**
 * OLED Display Pins (SSD1306, Software I2C)
 *
 * WARNING: Hardware I2C1 (PB6/PB7) CONFLICTS with TIM4 encoder (M2)!
 * ROSMaster board uses software I2C (bit-bang) on alternate pins.
 * Using PA2/PA3 which are free (not used by motors/encoders/USART1).
 */
#define OLED_USE_SOFTWARE_I2C       1           // Use software I2C (bit-bang)
#define OLED_SCL_PORT               GPIOA
#define OLED_SCL_PIN                GPIO_Pin_2  // PA2 (Software I2C SCL)
#define OLED_SDA_PORT               GPIOA
#define OLED_SDA_PIN                GPIO_Pin_3  // PA3 (Software I2C SDA)
#define OLED_I2C_ADDRESS            0x3C        // 7-bit address

/**
 * Serial Communication (USART1 via Micro-USB)
 */
#define USART_TX_PIN                GPIO_Pin_9  // PA9 (USART1_TX)
#define USART_TX_PORT               GPIOA
#define USART_RX_PIN                GPIO_Pin_10 // PA10 (USART1_RX)
#define USART_RX_PORT               GPIOA

/**
 * Buzzer Pin (Active buzzer via SS8050 NPN transistor)
 * ROSMaster V3.0: PC5 controls buzzer
 */
#define BUZZER_PORT                 GPIOC
#define BUZZER_PIN                  GPIO_Pin_5  // PC5
#define BUZZER_GPIO_CLK             RCC_APB2Periph_GPIOC
#define BUZZER_ON()                 GPIO_SetBits(BUZZER_PORT, BUZZER_PIN)
#define BUZZER_OFF()                GPIO_ResetBits(BUZZER_PORT, BUZZER_PIN)

/**
 * User Button (KEY1)
 * ROSMaster V3.0: PD2 with internal pull-up, active-low
 */
#define KEY1_PORT                   GPIOD
#define KEY1_PIN                    GPIO_Pin_2  // PD2
#define KEY1_GPIO_CLK               RCC_APB2Periph_GPIOD
#define KEY1_PRESSED()              (!GPIO_ReadInputDataBit(KEY1_PORT, KEY1_PIN))

/**
 * LED Pins (for status indication)
 * ROSMaster V3.0 board LEDs
 */
#define LED1_PORT                   GPIOD
#define LED1_PIN                    GPIO_Pin_3  // PD3
#define LED1_GPIO_CLK               RCC_APB2Periph_GPIOD
#define LED2_PORT                   GPIOD
#define LED2_PIN                    GPIO_Pin_4  // PD4
#define LED2_GPIO_CLK               RCC_APB2Periph_GPIOD

/* ========================================================================
 * DERIVED CONSTANTS (DO NOT MODIFY)
 * ======================================================================== */

/**
 * Kinematics Helper Constants
 * Used in mecanum inverse/forward kinematics calculations
 */
#define HALF_WHEEL_BASE             (WHEEL_BASE_M / 2.0f)
#define HALF_TRACK_WIDTH            (TRACK_WIDTH_M / 2.0f)
#define WHEELBASE_PLUS_TRACK        (HALF_WHEEL_BASE + HALF_TRACK_WIDTH)

/**
 * Encoder to Velocity Conversion
 * wheel_velocity (m/s) = (encoder_delta / ENCODER_EDGES_PER_REV)
 *                        × (2π × WHEEL_RADIUS_M)
 *                        × CONTROL_LOOP_RATE_HZ
 */
#define ENCODER_TO_MPS_FACTOR       ((2.0f * PI_F * WHEEL_RADIUS_M) / ENCODER_EDGES_PER_REV)

/**
 * Task Stack Sizes (FreeRTOS)
 */
#define TASK_CONTROL_STACK          512
#define TASK_COMMUNICATION_STACK    512  // G8: Increased from 256 for flash_storage_save() depth
#define TASK_IMU_STACK              1024
#define TASK_MONITORING_STACK       512

/**
 * Total FreeRTOS Heap Size
 */
#define FREERTOS_HEAP_SIZE          (20 * 1024)  // 20KB

#endif // ORBIBOT_CONFIG_H
