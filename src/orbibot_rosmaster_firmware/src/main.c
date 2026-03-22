/**
 * @file main.c
 * @brief OrbiBot ROSMaster Firmware - Main Application Entry Point
 * @author Jewel Nath
 * @date 2025-11-27
 *
 * This is the main entry point for the OrbiBot firmware. It initializes
 * all hardware, creates FreeRTOS tasks, and starts the scheduler.
 *
 * Boot Sequence:
 * 1. System clock configuration (72MHz)
 * 2. Hardware initialization (GPIO, timers, USART, SPI, I2C, ADC)
 * 3. Driver initialization (motors, encoders, IMU, battery)
 * 4. FreeRTOS task creation
 * 5. Start scheduler (never returns)
 */

#include "stm32f10x.h"
#include "stm32f10x_flash.h"
#include "stm32f10x_rcc.h"
#include "orbibot_config.h"
#include "firmware_version.h"
#include "FreeRTOS.h"
#include "task.h"

extern void xPortSysTickHandler(void);

// HAL headers
#include "hal_gpio.h"
#include "hal_usart.h"
#include "hal_timer.h"
#include "hal_spi.h"
#include "hal_i2c.h"
#include "hal_adc.h"
#include "hal_watchdog.h"

// Driver headers
#include "motor_driver.h"
#include "encoder_driver.h"
#include "imu_driver.h"
#include "battery_monitor.h"

#if ENABLE_OLED_DISPLAY
#include "oled_driver.h"
#endif

// Task headers
#include "task_control.h"
#include "task_communication.h"
#include "task_imu.h"
#include "task_monitoring.h"

// Protocol header
#include "protocol.h"

// Global system state
volatile uint8_t system_initialized = 0;
volatile uint32_t system_uptime_ms = 0;

/**
 * @brief System clock configuration
 *
 * Configures the system clock to 72MHz using:
 * - HSE (High-Speed External): 8MHz crystal
 * - PLL multiplier: ×9
 * - System clock: 72MHz
 * - AHB clock: 72MHz
 * - APB1 clock: 36MHz
 * - APB2 clock: 72MHz
 */
static void systemClockConfig(void)
{
    // Try HSE (8MHz external crystal) -> PLL -> 72MHz
    RCC_HSEConfig(RCC_HSE_ON);
    ErrorStatus hse_status = RCC_WaitForHSEStartUp();

    if (hse_status == SUCCESS)
    {
        // HSE OK: configure PLL for 72MHz (HSE × 9)
        FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable);
        FLASH_SetLatency(FLASH_Latency_2);

        RCC_PLLConfig(RCC_PLLSource_HSE_Div1, RCC_PLLMul_9);
        RCC_PLLCmd(ENABLE);
        while (RCC_GetFlagStatus(RCC_FLAG_PLLRDY) == RESET);

        RCC_SYSCLKConfig(RCC_SYSCLKSource_PLLCLK);
        while (RCC_GetSYSCLKSource() != 0x08);
    }
    else
    {
        // HSE failed — fall back to HSI (8MHz internal RC).
        // PLL from HSI/2 × 9 = 36MHz (half speed, degraded but functional).
        RCC_HSEConfig(RCC_HSE_OFF);

        FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable);
        FLASH_SetLatency(FLASH_Latency_1);  // 1 wait state for 36MHz

        RCC_PLLConfig(RCC_PLLSource_HSI_Div2, RCC_PLLMul_9);
        RCC_PLLCmd(ENABLE);
        while (RCC_GetFlagStatus(RCC_FLAG_PLLRDY) == RESET);

        RCC_SYSCLKConfig(RCC_SYSCLKSource_PLLCLK);
        while (RCC_GetSYSCLKSource() != 0x08);
    }

    // Configure AHB clock (HCLK = SYSCLK = 72MHz)
    RCC_HCLKConfig(RCC_SYSCLK_Div1);

    // Configure APB1 clock (PCLK1 = HCLK/2 = 36MHz, max 36MHz)
    RCC_PCLK1Config(RCC_HCLK_Div2);

    // Configure APB2 clock (PCLK2 = HCLK = 72MHz)
    RCC_PCLK2Config(RCC_HCLK_Div1);

    // Update SystemCoreClock variable
    SystemCoreClockUpdate();
}

/**
 * @brief Hardware initialization
 *
 * Initializes all hardware peripherals in the correct order:
 * 1. GPIO pins
 * 2. USART (for printf debugging)
 * 3. Timers (PWM and encoders)
 * 4. SPI (for IMU)
 * 5. I2C (for OLED)
 * 6. ADC (for battery monitoring)
 */
static void hardwareInit(void)
{
    // Configure NVIC priority grouping (Group 2)
    // Group 2: 2 bits for preemption priority, 2 bits for sub-priority
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);

    // Initialize GPIO pins (motors, LEDs, etc.)
    hal_gpio_init();

    // Initialize USART for serial communication
    hal_usart_init(USART_BAUDRATE);

    // Print startup message
    BOOT_PRINTF("\n\n");
    BOOT_PRINTF("========================================\n");
    BOOT_PRINTF("%s\n", FIRMWARE_FULL_INFO);
    BOOT_PRINTF("========================================\n");
    BOOT_PRINTF("Target: %s\n", FIRMWARE_TARGET);
    BOOT_PRINTF("Board: %s\n", FIRMWARE_BOARD);
    BOOT_PRINTF("System Clock: %lu MHz\n", SystemCoreClock / 1000000);
    BOOT_PRINTF("Build: %s %s\n", BUILD_DATE, BUILD_TIME);
    BOOT_PRINTF("========================================\n\n");

    // Initialize timers (PWM for motors, capture for encoders)
    BOOT_PRINTF("[INIT] Configuring timers...\n");
    hal_timer_init();

    // Initialize SPI for IMU communication
    BOOT_PRINTF("[INIT] Configuring SPI for IMU...\n");
    hal_spi_init();

#if ENABLE_OLED_DISPLAY
    // Initialize I2C for OLED display
    BOOT_PRINTF("[INIT] Configuring I2C for OLED...\n");
    hal_i2c_init();
#endif

    // Initialize ADC for battery monitoring
    BOOT_PRINTF("[INIT] Configuring ADC for battery...\n");
    hal_adc_init();

    BOOT_PRINTF("[INIT] Hardware initialization complete.\n\n");
}

/**
 * @brief Motor test - briefly pulse each motor to verify PWM is working
 *
 * This test directly writes to timer CCR registers to verify the PWM
 * hardware is configured correctly. Motors should briefly twitch.
 */
__attribute__((unused))
static void motorTest(void)
{
    BOOT_PRINTF("[TEST] Motor PWM test - pulsing each motor...\n");

    // Use direct register access to eliminate software layers
    // Motor to Timer mapping (ROSMaster V3.0):
    //   M1 (Front-Left):  TIM8 CCR1/CCR2 -> PA11/PA8
    //   M2 (Back-Left):   TIM8 CCR3/CCR4 -> PB0/PB1
    //   M3 (Front-Right): TIM1 CCR4/CCR1 -> PC6/PC7
    //   M4 (Back-Right):  TIM1 CCR2/CCR3 -> PC8/PC9 (via CH2N/CH3N)

    // Test M1 (Front-Left): TIM8 CCR1/CCR2 (PA11/PA8)
    BOOT_PRINTF("  M1 (FL): TIM8->CCR1 = 2000 (PA11)\n");
    TIM8->CCR1 = 2000;
    TIM8->CCR2 = 0;
    for (volatile int i = 0; i < 500000; i++);  // ~70ms delay
    TIM8->CCR1 = 0;

    // Test M2 (Back-Left): TIM8 CCR3/CCR4 (PB0/PB1)
    BOOT_PRINTF("  M2 (BL): TIM8->CCR3 = 2000 (PB0)\n");
    TIM8->CCR3 = 2000;
    TIM8->CCR4 = 0;
    for (volatile int i = 0; i < 500000; i++);
    TIM8->CCR3 = 0;

    // Test M3 (Front-Right): TIM1 CCR4/CCR1 (PC6/PC7)
    BOOT_PRINTF("  M3 (FR): TIM1->CCR4 = 2000 (PC6)\n");
    TIM1->CCR4 = 2000;
    TIM1->CCR1 = 0;
    for (volatile int i = 0; i < 500000; i++);
    TIM1->CCR4 = 0;

    // Test M4 (Back-Right): TIM1 CCR2/CCR3 (PC8/PC9 via CH2N/CH3N)
    BOOT_PRINTF("  M4 (BR): TIM1->CCR2 = 2000 (PC8 via CH2N)\n");
    TIM1->CCR2 = 2000;
    TIM1->CCR3 = 0;
    for (volatile int i = 0; i < 500000; i++);
    TIM1->CCR2 = 0;

    BOOT_PRINTF("[TEST] Motor test complete - did motors twitch?\n\n");
}

/**
 * @brief Driver initialization
 *
 * Initializes device drivers that depend on HAL:
 * - Motor driver
 * - Encoder driver
 * - IMU driver
 * - Battery monitor
 * - OLED display (optional)
 */
static void driverInit(void)
{
    BOOT_PRINTF("[INIT] Initializing drivers...\n");

    BOOT_PRINTF("[INIT] Motor driver...\n");
    motor_driver_init();

#if ENABLE_BOOT_MESSAGES
    motorTest();
#endif

    BOOT_PRINTF("[INIT] Encoder driver...\n");
    encoder_driver_init();

    BOOT_PRINTF("[INIT] IMU driver (ICM-20948)...\n");
    if (imu_driver_init() == 0)
    {
        BOOT_PRINTF("[OK] IMU initialized successfully\n");
    }
    else
    {
        // FATAL: IMU is mandatory for OrbiBot odometry and heading control.
        // Continuing without IMU causes task_imu to read garbage SPI data that
        // looks like valid sensor output, silently corrupting odometry.
        // Halt here so the fault is visible (boot messages stop; no auto-report).
        BOOT_PRINTF("[FATAL] IMU initialization failed — check SPI2 wiring (PB12-PB15) "
                    "and ICM-20948 WHO_AM_I (expected 0xEA). Halting.\n");
        while (1)
        {
            // Hold here. Watchdog will eventually reset the MCU for a retry.
        }
    }

    BOOT_PRINTF("[INIT] Battery monitor...\n");
    battery_monitor_init();

#if ENABLE_OLED_DISPLAY
    BOOT_PRINTF("[INIT] OLED display...\n");
    if (oled_driver_init() == 0)
    {
        BOOT_PRINTF("[OK] OLED initialized successfully\n");
        oled_clear();
        oled_print(0, 0, "OrbiBot v1.0");
        oled_print(0, 1, "Initializing...");
        oled_update();
    }
    else
    {
        BOOT_PRINTF("[WARN] OLED not detected\n");
    }
#endif

    BOOT_PRINTF("[INIT] Driver initialization complete.\n\n");
}

/**
 * @brief Initialize communication protocol
 */
static void protocolInit(void)
{
    BOOT_PRINTF("[INIT] Initializing communication protocol...\n");
    protocol_init();
    BOOT_PRINTF("[INIT] Protocol ready (ROSMaster compatible)\n\n");
}

/**
 * @brief Create FreeRTOS tasks
 *
 * Creates all application tasks with appropriate priorities:
 * - Priority 10: Control task (motor PID, highest priority)
 * - Priority 9: Communication task (serial RX/TX)
 * - Priority 8: IMU task (sensor data acquisition)
 * - Priority 5: Monitoring task (battery, diagnostics)
 */
static void createTasks(void)
{
    BOOT_PRINTF("[RTOS] Creating FreeRTOS tasks...\n");

    // Task 1: Motion control (highest priority)
    BaseType_t result = xTaskCreate(
        task_control,                   // Task function
        "ControlTask",                  // Task name
        TASK_CONTROL_STACK,             // Stack size
        NULL,                           // Parameters
        10,                             // Priority (highest)
        NULL                            // Task handle
    );
    if (result != pdPASS)
    {
        BOOT_PRINTF("[ERROR] Failed to create ControlTask\n");
        while (1);
    }
    BOOT_PRINTF("[RTOS] Created ControlTask (priority 10, %d bytes stack)\n", TASK_CONTROL_STACK * 4);

    // Task 2: Serial communication (auto-report)
    // Priority 7 - lower than control tasks, runs in gaps (matches reference firmware)
    result = xTaskCreate(
        task_communication,
        "CommTask",
        TASK_COMMUNICATION_STACK,
        NULL,
        7,
        NULL
    );
    if (result != pdPASS)
    {
        BOOT_PRINTF("[ERROR] Failed to create CommTask\n");
        while (1);
    }
    BOOT_PRINTF("[RTOS] Created CommTask (priority 7, %d bytes stack)\n", TASK_COMMUNICATION_STACK * 4);

    // Task 3: IMU data acquisition
    result = xTaskCreate(
        task_imu,
        "IMU_Task",
        TASK_IMU_STACK,
        NULL,
        8,
        NULL
    );
    if (result != pdPASS)
    {
        BOOT_PRINTF("[ERROR] Failed to create IMU_Task\n");
        while (1);
    }
    BOOT_PRINTF("[RTOS] Created IMU_Task (priority 8, %d bytes stack)\n", TASK_IMU_STACK * 4);

    // Task 4: System monitoring (battery, diagnostics)
    result = xTaskCreate(
        task_monitoring,
        "MonitorTask",
        TASK_MONITORING_STACK,
        NULL,
        5,
        NULL
    );
    if (result != pdPASS)
    {
        BOOT_PRINTF("[ERROR] Failed to create MonitorTask\n");
        while (1);
    }
    BOOT_PRINTF("[RTOS] Created MonitorTask (priority 5, %d bytes stack)\n", TASK_MONITORING_STACK * 4);

    BOOT_PRINTF("[RTOS] All tasks created successfully.\n");
    BOOT_PRINTF("[RTOS] Total stack allocated: %d bytes\n",
           (TASK_CONTROL_STACK + TASK_COMMUNICATION_STACK +
            TASK_IMU_STACK + TASK_MONITORING_STACK) * 4);
    BOOT_PRINTF("[RTOS] FreeRTOS heap: %d bytes\n\n", FREERTOS_HEAP_SIZE);
}

/**
 * @brief Application entry point
 *
 * Main function that:
 * 1. Configures system clock
 * 2. Initializes hardware and drivers
 * 3. Creates FreeRTOS tasks
 * 4. Starts scheduler (never returns)
 */
int main(void)
{
    // Start watchdog FIRST — IWDG uses internal LSI (independent of HSE/PLL).
    // If systemClockConfig() hangs on HSE failure, the IWDG resets MCU after 5s.
#if ENABLE_WATCHDOG
    hal_watchdog_init();
#endif

    // Configure system clock to 72MHz
    systemClockConfig();

    // Initialize all hardware peripherals
    hardwareInit();

    // Initialize device drivers
    driverInit();

    // Initialize communication protocol
    protocolInit();

    // Initialize control task
    task_control_init();

    // Set system initialized flag
    system_initialized = 1;

    // Create FreeRTOS tasks
    createTasks();

    // Print final startup message
    BOOT_PRINTF("========================================\n");
    BOOT_PRINTF("OrbiBot firmware initialization complete!\n");
    BOOT_PRINTF("Starting FreeRTOS scheduler...\n");
    BOOT_PRINTF("========================================\n\n");

#if ENABLE_OLED_DISPLAY
    // Show ready message
    oled_show_ready();
#endif

    // Start FreeRTOS scheduler (never returns)
    vTaskStartScheduler();

    // Should never reach here
    BOOT_PRINTF("[ERROR] FreeRTOS scheduler failed to start!\n");
    while (1);

    return 0;
}

/**
 * @brief SysTick interrupt handler (called by FreeRTOS)
 *
 * This is called every 1ms by the FreeRTOS tick interrupt.
 * We use it to track system uptime.
 */
/**
 * @brief SVC Handler - Required by FreeRTOS for task switching
 */
void SVC_Handler(void)
{
    extern void vPortSVCHandler(void);
    vPortSVCHandler();
}

/**
 * @brief PendSV Handler - Required by FreeRTOS for context switching
 */
void PendSV_Handler(void)
{
    extern void xPortPendSVHandler(void);
    xPortPendSVHandler();
}

/**
 * @brief SysTick Handler - Required by FreeRTOS for timing
 */
void SysTick_Handler(void)
{
    // Update system uptime
    system_uptime_ms++;

    // Call FreeRTOS tick handler
    xPortSysTickHandler();
}

/**
 * @brief Get system uptime in milliseconds
 * @return Uptime in milliseconds since boot
 */
uint32_t system_get_uptime_ms(void)
{
    return system_uptime_ms;
}

/**
 * @brief Check if system is initialized
 * @return 1 if initialized, 0 otherwise
 */
uint8_t system_is_initialized(void)
{
    return system_initialized;
}

/**
 * @brief Direct USART1 output — safe in fault/ISR context.
 *
 * Uses raw register writes instead of printf/HAL to avoid any
 * dependency on heap, DMA, or library functions that may have
 * caused (or been corrupted by) the fault.
 */
static void fault_putc(char c)
{
    while (!(USART1->SR & (1 << 7)));  // Wait for TXE
    USART1->DR = (uint8_t)c;
}

static void fault_puts(const char *s)
{
    while (*s) fault_putc(*s++);
}

void vApplicationStackOverflowHook(TaskHandle_t pxTask, char *pcTaskName)
{
    (void)pxTask;
    __disable_irq();
    fault_puts("\n[FATAL] Stack overflow: ");
    fault_puts(pcTaskName);
    fault_puts("\n");
    while (1);
}

void vApplicationMallocFailedHook(void)
{
    __disable_irq();
    fault_puts("\n[FATAL] FreeRTOS heap exhausted!\n");
    while (1);
}

void HardFault_Handler(void)
{
    __disable_irq();
    fault_puts("\n[FATAL] Hard fault exception!\n");
    while (1);
}
