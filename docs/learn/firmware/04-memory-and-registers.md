---
title: "Part 0: Memory and Registers"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "25 minutes"
tags:
  - learn
  - firmware
---

# Part 0: Memory and Registers

**Duration**: 25 minutes  
**Prerequisites**: [[03-number-systems]]

---

## Learning Objectives

After this lesson, you will understand:
- Types of memory in microcontrollers
- What registers are and how they work
- Memory map of STM32F103
- How to access hardware via registers
- The difference between RAM, Flash, and registers

---

## Types of Memory in STM32

The STM32F103 has three main types of memory:

```
┌─────────────────────────────────────────────────────────┐
│              STM32F103RCT6 Memory Layout                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  FLASH MEMORY (256 KB)                                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │  0x0800 0000                                    │    │
│  │  ┌─────────────┐                                │    │
│  │  │   Vector    │ ← Interrupt vectors            │    │
│  │  │   Table     │                                │    │
│  │  ├─────────────┤                                │    │
│  │  │             │                                │    │
│  │  │   Program   │ ← Your firmware code           │    │
│  │  │    Code     │                                │    │
│  │  │             │                                │    │
│  │  ├─────────────┤                                │    │
│  │  │   Const     │ ← Constants, strings           │    │
│  │  │   Data      │                                │    │
│  │  └─────────────┘                                │    │
│  │  0x0803 FFFF                                    │    │
│  └─────────────────────────────────────────────────┘    │
│  • Non-volatile (keeps data without power)              │
│  • Read-only during normal operation                    │
│  • Used for program storage                             │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  SRAM (48 KB)                                            │
│  ┌─────────────────────────────────────────────────┐    │
│  │  0x2000 0000                                    │    │
│  │  ┌─────────────┐                                │    │
│  │  │   .data     │ ← Initialized globals          │    │
│  │  ├─────────────┤                                │    │
│  │  │   .bss      │ ← Zero-initialized globals     │    │
│  │  ├─────────────┤                                │    │
│  │  │    Heap     │ ← Dynamic allocation           │    │
│  │  │   (↓ grows  │                                │    │
│  │  │    down)    │                                │    │
│  │  ├─────────────┤                                │    │
│  │  │    Stack    │ ← Local variables,             │    │
│  │  │   (↑ grows  │   function calls               │    │
│  │  │    up)      │                                │    │
│  │  └─────────────┘                                │    │
│  │  0x2000 BFFF                                    │    │
│  └─────────────────────────────────────────────────┘    │
│  • Volatile (lost when power off)                       │
│  • Fast read/write                                      │
│  • Used for variables and runtime data                  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PERIPHERAL REGISTERS                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  0x4000 0000 - 0x4001 3FFF  (APB1, APB2)       │    │
│  │  0x4002 0000 - 0x4002 3FFF  (AHB)              │    │
│  │                                                  │    │
│  │  GPIOA: 0x4001 0800                             │    │
│  │  GPIOB: 0x4001 0C00                             │    │
│  │  TIM1:  0x4001 2C00                             │    │
│  │  USART1: 0x4001 3800                            │    │
│  │  SPI1:  0x4001 3000                             │    │
│  │  ...                                            │    │
│  └─────────────────────────────────────────────────┘    │
│  • Special memory-mapped hardware control               │
│  • Read/write configures hardware behavior              │
│  • Each peripheral has specific registers               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Flash Memory (Program Storage)

### What is Flash?

Flash memory stores your compiled program. It keeps data even without power.

```c
// This code is stored in FLASH
void main(void) {
    // Function instructions stored in Flash
    int x = 10;  // This line compiled to machine code in Flash
    
    while(1) {
        // Loop instructions in Flash
    }
}

// Constant data also in Flash
const char message[] = "Hello World";  // Stored in Flash
const int table[100] = {0, 1, 2, ...}; // Stored in Flash
```

### Flash Characteristics

| Property | Value |
|----------|-------|
| Size | 256 KB |
| Read Speed | Fast (zero wait states at 72MHz) |
| Write Speed | Slow (must erase before write) |
| Endurance | 10,000 write cycles |
| Retention | 30 years |

### Flash Usage Example

```c
// Flash storage for persistent data (OrbiBot)
// Stores PID gains and calibration

// Write to flash (slow, only when needed)
void save_calibration(void) {
    // Erase flash sector
    FLASH_ErasePage(CALIBRATION_ADDRESS);
    
    // Write data
    FLASH_ProgramWord(CALIBRATION_ADDRESS, pid_kp);
    FLASH_ProgramWord(CALIBRATION_ADDRESS + 4, pid_ki);
    FLASH_ProgramWord(CALIBRATION_ADDRESS + 8, pid_kd);
}

// Read from flash (fast, normal operation)
void load_calibration(void) {
    pid_kp = *(float *)CALIBRATION_ADDRESS;
    pid_ki = *(float *)(CALIBRATION_ADDRESS + 4);
    pid_kd = *(float *)(CALIBRATION_ADDRESS + 8);
}
```

---

## SRAM (Runtime Memory)

### What is SRAM?

Static RAM is where variables live during program execution. It's fast but loses data when power is off.

```c
// These go to SRAM
int global_var = 10;           // .data section (initialized)
int uninitialized_var;          // .bss section (zero-initialized)
static int static_var;          // Also in SRAM

void function(void) {
    int local_var = 5;          // Stack (in SRAM)
    int array[100];             // Stack (in SRAM)
    
    int *ptr = malloc(50);      // Heap (in SRAM)
    free(ptr);
}
```

### Memory Sections

```
SRAM Layout:

High Address (0x2000 BFFF)
┌─────────────────────────┐
│                         │
│    Stack (grows down)   │ ← Function calls, local variables
│          ↓              │
├─────────────────────────┤
│                         │
│                         │
│    Free Space           │
│                         │
│                         │
├─────────────────────────┤
│          ↑              │
│    Heap (grows up)      │ ← malloc/free allocations
├─────────────────────────┤
│    .bss (uninitialized) │ ← Zero-initialized globals
├─────────────────────────┤
│    .data (initialized)  │ ← Globals with initial values
├─────────────────────────┤
Low Address (0x2000 0000)
```

### Stack vs Heap

| Feature | Stack | Heap |
|---------|-------|------|
| **Allocation** | Automatic | Manual (malloc/free) |
| **Speed** | Fast | Slower |
| **Size** | Fixed at startup | Grows dynamically |
| **Lifetime** | Function scope | Until freed |
| **Use for** | Local variables | Large buffers, dynamic data |

```c
// STACK (automatic)
void function(void) {
    int x;              // Stack allocation
    char buffer[100];   // Stack allocation
}                       // Automatically freed when function returns

// HEAP (manual)
void function(void) {
    char *buffer = malloc(1000);  // Heap allocation
    
    // Use buffer...
    
    free(buffer);       // Must manually free!
}
```

---

## Registers

### What are Registers?

Registers are special memory locations that control hardware. Writing to a register changes hardware behavior.

```c
// GPIO Register example
#define GPIOA_BASE   0x40010800

// Register structure (each offset is 4 bytes)
typedef struct {
    volatile uint32_t CRL;   // 0x00: Config Low (pins 0-7)
    volatile uint32_t CRH;   // 0x04: Config High (pins 8-15)
    volatile uint32_t IDR;   // 0x08: Input Data
    volatile uint32_t ODR;   // 0x0C: Output Data
    volatile uint32_t BSRR;  // 0x10: Bit Set/Reset
    volatile uint32_t BRR;   // 0x14: Bit Reset
    volatile uint32_t LCKR;  // 0x18: Lock
} GPIO_TypeDef;

#define GPIOA ((GPIO_TypeDef *)GPIOA_BASE)

// Use registers
GPIOA->ODR = 0x0001;     // Set pin A0 HIGH
uint8_t pin = GPIOA->IDR; // Read all pins
```

### Register Access Example

```c
// Turn on LED connected to PA5

// Method 1: Direct register access (fastest)
GPIOA->ODR |= (1 << 5);   // Set bit 5 (PA5)

// Method 2: Using BSRR register (atomic)
GPIOA->BSRR = (1 << 5);   // Set PA5 (no read-modify-write)

// Method 3: Reset via BRR
GPIOA->BRR = (1 << 5);    // Clear PA5 (set LOW)
```

---

## Memory Map

### STM32F103 Memory Map

```
Address Range        | Usage
─────────────────────────────────────────
0x0000 0000 - 0x07FF FFFF  | Flash (Aliased)
0x0800 0000 - 0x0803 FFFF  | Flash (256 KB)
                           |
0x1FFF F000 - 0x1FFF F7FF  | System Memory (Bootloader)
0x1FFF F800 - 0x1FFF F80F  | Option Bytes
                           |
0x2000 0000 - 0x2000 BFFF  | SRAM (48 KB)
                           |
0x4000 0000 - 0x4000 77FF  | APB1 Peripherals
                           |   TIM2, TIM3, TIM4, TIM5
                           |   USART2, USART3, UART4, UART5
                           |   SPI2, SPI3, I2C1, I2C2
                           |   CAN, USB, etc.
                           |
0x4001 0000 - 0x4001 3FFF  | APB2 Peripherals
                           |   GPIOA, GPIOB, GPIOC, GPIOD
                           |   USART1, SPI1, TIM1, ADC1, ADC2
                           |
0x4002 0000 - 0x4002 3FFF  | AHB Peripherals
                           |   DMA, RCC, Flash Interface
                           |
0xE000 0000 - 0xE00F FFFF  | Cortex-M3 Internal
                           |   NVIC, SysTick, Debug
```

### Peripheral Base Addresses

| Peripheral | Base Address | Used In OrbiBot |
|------------|--------------|-----------------|
| GPIOA | 0x4001 0800 | LEDs, TIM2 remap |
| GPIOB | 0x4001 0C00 | I2C, SPI2, TIM3/4 |
| GPIOC | 0x4001 1000 | Motor PWM (TIM1) |
| TIM1 | 0x4001 2C00 | Motor PWM (M3, M4) |
| TIM2 | 0x4000 0000 | Encoder (M1) |
| TIM3 | 0x4000 0400 | Encoder (M4) |
| TIM4 | 0x4000 0800 | Encoder (M2) |
| USART1 | 0x4001 3800 | Serial to Pi |
| SPI1 | 0x4001 3000 | Not used |
| SPI2 | 0x4000 3800 | IMU (ICM-20948) |
| I2C1 | 0x4000 5400 | Not used (conflict) |
| I2C2 | 0x4000 5800 | OLED display |
| ADC1 | 0x4001 2400 | Battery monitoring |

---

## Register Programming Example

### GPIO Configuration

```c
// Configure PA5 as output (push-pull, 50MHz)

// 1. Enable GPIOA clock (RCC register)
RCC->APB2ENR |= (1 << 2);  // Enable GPIOA clock

// 2. Configure pin mode (CRL for pins 0-7)
// Each pin uses 4 bits: CNF[1:0] + MODE[1:0]
// Pin 5: bits 20-23 in CRL
// Mode 11 (50MHz output) + CNF 00 (Push-Pull)

GPIOA->CRL &= ~(0xF << 20);  // Clear bits 20-23
GPIOA->CRL |=  (0x3 << 20);  // Set mode: 50MHz output

// 3. Use the pin
GPIOA->ODR |= (1 << 5);   // PA5 HIGH
GPIOA->ODR &= ~(1 << 5);  // PA5 LOW
```

### Timer Configuration

```c
// Configure TIM2 for 1ms interrupt

// 1. Enable TIM2 clock
RCC->APB1ENR |= (1 << 0);

// 2. Set prescaler (72MHz / 72 = 1MHz)
TIM2->PSC = 72 - 1;

// 3. Set auto-reload (1MHz / 1000 = 1kHz = 1ms)
TIM2->ARR = 1000 - 1;

// 4. Enable update interrupt
TIM2->DIER |= (1 << 0);

// 5. Enable timer
TIM2->CR1 |= (1 << 0);
```

---

## Volatile Keyword

### Why Use volatile?

```c
// WITHOUT volatile - compiler may optimize away reads
uint32_t status = GPIOA->IDR;  // Read once
while (status & (1 << 0)) {    // Compiler thinks this never changes!
    // Loop forever (wrong!)
}

// WITH volatile - forces actual memory read
volatile uint32_t status = GPIOA->IDR;  // Read from hardware
while (status & (1 << 0)) {             // Read fresh each time
    // Correct - checks actual pin state
}
```

### When to Use volatile

```c
// ALWAYS use volatile for:
// 1. Hardware registers
volatile uint32_t * const GPIOA_ODR = (uint32_t *)0x4001080C;

// 2. Variables modified by ISRs
volatile uint32_t interrupt_count = 0;

void TIM2_IRQHandler(void) {
    interrupt_count++;  // Modified by ISR
}

// 3. Shared variables between tasks (RTOS)
volatile uint32_t shared_data;
```

---

## Exercise: Register Access

**Task**: Write code to configure PB0 as output and toggle it every 500ms.

**Hints**:
- GPIOB base: 0x4001 0C00
- RCC_APB2ENR: 0x4002 1018
- Use bit 3 to enable GPIOB clock
- PB0 uses CRL bits 0-3

**Answer**:

<details>
<summary>Click for answer</summary>

```c
// Register definitions
#define RCC_BASE     0x40021000
#define RCC_APB2ENR  (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define GPIOB_BASE   0x40010C00
#define GPIOB_CRL    (*(volatile uint32_t *)(GPIOB_BASE + 0x00))
#define GPIOB_ODR    (*(volatile uint32_t *)(GPIOB_BASE + 0x0C))

int main(void) {
    // 1. Enable GPIOB clock (bit 3)
    RCC_APB2ENR |= (1 << 3);
    
    // 2. Configure PB0 as output (mode 11 = 50MHz)
    // CRL bits 3:0 for pin 0
    GPIOB_CRL &= ~(0xF << 0);  // Clear
    GPIOB_CRL |=  (0x3 << 0);  // Set: 50MHz push-pull
    
    // 3. Toggle loop
    while(1) {
        GPIOB_ODR ^= (1 << 0);  // Toggle PB0
        
        // Simple delay
        for(volatile int i = 0; i < 500000; i++);
    }
}
```

</details>

---

## Summary

- **Flash** (256KB): Program storage, non-volatile
- **SRAM** (48KB): Runtime variables, volatile
- **Registers**: Hardware control via memory-mapped addresses
- **Stack**: Local variables, automatic allocation
- **Heap**: Dynamic allocation (malloc/free)
- **volatile**: Prevents compiler optimization for hardware access

---

## Next Lesson

[[10-stm32-introduction]] - Detailed STM32F103 overview

---

*OrbiBot Firmware Study Guide*  
*Part 0 of 10*