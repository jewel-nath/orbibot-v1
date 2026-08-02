---
title: "Part 1: STM32 Introduction"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "20 minutes"
tags:
  - learn
  - firmware
---

# Part 1: STM32 Introduction

**Duration**: 20 minutes  
**Prerequisites**: [[04-memory-and-registers]]

---

## Learning Objectives

After this lesson, you will understand:
- What the STM32F103 is
- Key specifications of the MCU
- Why it was chosen for OrbiBot
- Basic architecture overview

---

## What is STM32F103?

The **STM32F103RCT6** is the microcontroller that powers OrbiBot.

```
┌─────────────────────────────────────────┐
│           STM32F103RCT6                 │
│                                         │
│  • ARM Cortex-M3 processor              │
│  • 72 MHz maximum clock speed           │
│  • 256 KB Flash (program storage)       │
│  • 48 KB SRAM (runtime memory)          │
│  • 64 pins (LQFP package)               │
│  • Operating voltage: 2.0V - 3.6V       │
│                                         │
└─────────────────────────────────────────┘
```

---

## Key Specifications

| Feature | Value | For OrbiBot |
|---------|-------|-------------|
| **Core** | ARM Cortex-M3 | Industry standard, well-supported |
| **Clock** | 72 MHz | Fast enough for 100Hz control |
| **Flash** | 256 KB | Stores firmware + calibration data |
| **RAM** | 48 KB | FreeRTOS + variables + stack |
| **GPIO** | 51 pins | Motors, encoders, sensors, LEDs |
| **Timers** | 8 (16-bit) | PWM, encoder capture, timing |
| **ADC** | 2× 12-bit | Battery monitoring |
| **UART** | 3 | Serial to Raspberry Pi |
| **SPI** | 2 | IMU sensor communication |
| **I2C** | 2 | OLED display |
| **Price** | ~$2-3 | Affordable |

---

## Why STM32F103 for OrbiBot?

### 1. Sufficient Performance

```
Control loop requirements:
- 100 Hz update rate = 10ms period
- Each iteration: encoders + PID + motors
- Time needed: ~2-3 ms
- STM32 at 72 MHz: Plenty of headroom!
```

### 2. Good Peripheral Set

```
What we need              | What STM32 has
--------------------------|-------------------
4 motor PWM outputs       | 4 timers with PWM
4 encoder inputs          | 4 timers in encoder mode
Serial to Pi              | USART1 (with DMA option)
IMU (SPI)                 | SPI1 or SPI2
Battery ADC               | ADC1
OLED (I2C)                | I2C1 or I2C2
Status LEDs               | GPIO
```

### 3. Cost-Effective

```
STM32F103RCT6: ~$2.50 in quantity
Alternative (STM32F4): ~$8.00 (overkill)
Alternative (Arduino): Not powerful enough

Sweet spot for robotics!
```

---

## Architecture Overview

### Block Diagram

```
┌─────────────────────────────────────────┐
│           STM32F103 Block Diagram       │
├─────────────────────────────────────────┤
│                                         │
│   ┌─────────────┐                       │
│   │ Cortex-M3   │  ← CPU core           │
│   │ 72 MHz      │                       │
│   └──────┬──────┘                       │
│          │                              │
│   ┌──────┴──────┐                       │
│   │    Bus      │                       │
│   │  Matrix     │                       │
│   └──────┬──────┘                       │
│          │                              │
│    ┌─────┼─────┬─────────┬─────────┐   │
│    ↓     ↓     ↓         ↓         ↓   │
│ ┌────┐ ┌────┐ ┌────┐  ┌────┐  ┌────┐  │
│ │256K│ │48K │ │GPIO│  │TIM │  │ADC │  │
│ │Flash│ │SRAM│ │    │  │    │  │    │  │
│ └────┘ └────┘ └────┘  └────┘  └────┘  │
│                         ↑              │
│                    ┌────┴────┐         │
│                    │ USART   │         │
│                    │ SPI     │         │
│                    │ I2C     │         │
│                    └─────────┘         │
│                                         │
└─────────────────────────────────────────┘
```

---

## Clock System

### How 72 MHz is Generated

```
External Crystal: 8 MHz
         ↓
    PLL Multiplier: ×9
         ↓
    System Clock: 72 MHz
         ↓
    ┌────┬────┬────┐
    ↓    ↓    ↓    ↓
  CPU  AHB   APB1  APB2
 72MHz 72MHz 36MHz 72MHz
              ↑     ↑
           TIM2-7  TIM1,USART1,SPI1
```

---

## Memory Map (Review)

```
0x0800 0000 ┌────────────┐ Flash (256 KB)
            │  Program   │
            │   Code     │
            └────────────┘
0x2000 0000 ┌────────────┐ SRAM (48 KB)
            │  Variables │
            │   Stack    │
            └────────────┘
0x4000 0000 ┌────────────┐ Peripherals
            │  GPIO      │
            │  Timers    │
            │  UART      │
            │  etc.      │
            └────────────┘
```

---

## Development Environment

### What You Need

1. **Hardware**:
   - STM32F103RCT6 board (OrbiBot has one!)
   - USB-to-Serial adapter for programming
   - BOOT0 jumper for bootloader mode

2. **Software**:
   - PlatformIO (recommended)
   - STM32CubeProgrammer (alternative)
   - Or: Keil MDK, STM32CubeIDE

3. **Programming**:
   - Serial bootloader (built-in)
   - No debugger needed for basic work

---

## Summary

- **STM32F103RCT6**: 72 MHz, 256KB Flash, 48KB RAM
- **Why chosen**: Good balance of performance, features, cost
- **Key peripherals**: Timers, UART, SPI, I2C, ADC
- **Development**: PlatformIO with serial bootloader

---

## Next Lesson

[[04-memory-and-registers]] - Controlling pins through registers

---

*OrbiBot Firmware Study Guide*  
*Part 1 of 10*