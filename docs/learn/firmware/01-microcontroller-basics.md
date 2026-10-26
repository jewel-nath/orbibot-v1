# Part 0: Microcontroller Basics

**Duration**: 20 minutes  
**Prerequisites**: [Part 0: What is an Embedded System?](00-what-is-embedded.md)

---

## Learning Objectives

After this lesson, you will understand:
- What a microcontroller is
- How it differs from a microprocessor
- Key components inside a microcontroller
- Why STM32F103 was chosen for OrbiBot

---

## What is a Microcontroller?

A **microcontroller** is a small computer on a single chip. It contains:
- CPU (processor)
- Memory (RAM and Flash)
- Peripherals (GPIO, timers, communication interfaces)

All in one package!

### Visual Comparison

```
Microprocessor System (like PC):
┌─────────────────────────────────┐
│ Motherboard                     │
│  ┌────────┐   ┌────────┐       │
│  │  CPU   │   │  RAM   │       │ ← Separate chips
│  └────────┘   └────────┘       │
│  ┌────────┐   ┌────────┐       │
│  │ Storage│   │ GPU    │       │ ← More separate chips
│  └────────┘   └────────┘       │
│  ┌──────────────────┐          │
│  │ Other chips...   │          │
│  └──────────────────┘          │
└─────────────────────────────────┘

Microcontroller (STM32):
┌──────────────────┐
│ STM32F103RCT6    │
│                  │
│ ┌──┐ ┌────┐ ┌──┐ │
│ │CPU│ │RAM │ │  │ │
│ └──┘ └────┘ │Flash
│ ┌─────────┐  │  │ │
│ │GPIO,    │  └──┘ │
│ │Timers,  │        │
│ │SPI,UART │        │
│ └─────────┘        │
└──────────────────┘
```

---

## Microcontroller vs Microprocessor

| Feature | Microprocessor | Microcontroller |
|---------|----------------|-----------------|
| **CPU** | Yes | Yes |
| **RAM** | External (separate chip) | Built-in |
| **Storage** | External (SSD/HDD) | Built-in Flash |
| **I/O** | External chips needed | Built-in GPIO |
| **Power** | High (watts) | Low (milliwatts) |
| **Cost** | $100-$500 | $2-$10 |
| **Size** | Large | Small chip |
| **Use** | PCs, servers, phones | Appliances, robots, IoT |

### Analogy

```
Microprocessor = City Hospital
- Many specialized departments
- External equipment needed
- Expensive and large
- Can handle any medical case

Microcontroller = Village Clinic
- Essential equipment built-in
- Small and affordable
- Handles specific cases efficiently
- Perfect for common needs!
```

---

## Inside the STM32F103RCT6

### Specifications

| Feature | Value |
|---------|-------|
| Core | ARM Cortex-M3 (32-bit) |
| Clock Speed | 72 MHz |
| Flash Memory | 256 KB |
| RAM | 48 KB |
| GPIO Pins | 51 |
| Package | 64-pin LQFP |
| Operating Voltage | 3.3V |

### What Each Component Does

```
┌─────────────────────────────────────┐
│ STM32F103RCT6                       │
│                                     │
│ ┌─────────────┐                     │
│ │ ARM Cortex  │ ← CPU               │
│ │    -M3      │   72 million        │
│ │  (32-bit)   │   instructions/sec  │
│ └─────────────┘                     │
│                                     │
│ ┌─────────────┐                     │
│ │  256 KB     │ ← Flash             │
│ │   Flash     │   Stores your       │
│ │  (ROM)      │   program code      │
│ └─────────────┘                     │
│                                     │
│ ┌─────────────┐                     │
│ │   48 KB     │ ← RAM               │
│ │    RAM      │   Variables,        │
│ │             │   stack, heap       │
│ └─────────────┘                     │
│                                     │
│ ┌─────────────────────────┐         │
│ │    PERIPHERALS          │         │
│ │  ┌─────┐ ┌─────┐       │         │
│ │  │GPIO │ │Timer│ ← Control pins  │
│ │  │(51) │ │(8)  │   and timing    │
│ │  └─────┘ └─────┘       │         │
│ │  ┌─────┐ ┌─────┐       │         │
│ │  │SPI  │ │UART │ ← Talk to other │
│ │  │(3)  │ │(5)  │   devices       │
│ │  └─────┘ └─────┘       │         │
│ │  ┌─────┐ ┌─────┐       │         │
│ │  │I2C  │ │ADC  │ ← Sensors and   │
│ │  │(2)  │ │(2)  │   analog input  │
│ │  └─────┘ └─────┘       │         │
│ └─────────────────────────┘         │
└─────────────────────────────────────┘
```

---

## Why STM32F103 for OrbiBot?

### Advantages

1. **Affordable** (~$3 per chip)
2. **Fast enough** - 72 MHz handles 100Hz control loop easily
3. **Plenty of peripherals**:
   - 4 timers for 4 motor PWMs
   - 4 timers for 4 encoder inputs
   - SPI for IMU
   - UART for Raspberry Pi
4. **5V tolerant** pins - compatible with many sensors
5. **Large community** - lots of examples and help online

### Limitations

1. **No floating-point unit (FPU)** - math with decimals is slower
2. **Limited RAM** - 48KB requires careful memory management
3. **Older chip** - released in 2007 (but still popular!)

### Firmware Size Comparison

```
Yahboom Original Firmware:
- ~150 KB (uses Keil compiler)
- Bloated with unused features

OrbiBot Custom Firmware:
- ~38 KB (uses GCC + PlatformIO)
- Optimized for OrbiBot only
- 75% smaller!
```

---

## ARM Cortex-M3 Architecture

The CPU inside STM32F103 is an **ARM Cortex-M3**:

```
┌──────────────────────────────────────┐
│ ARM Cortex-M3 Core                   │
│                                      │
│  ┌─────────────┐    ┌──────────┐    │
│  │ Instruction │←───│ Program  │    │
│  │   Decoder   │    │ Counter  │    │
│  └──────┬──────┘    └──────────┘    │
│         ↓                            │
│  ┌───────────────────────────┐      │
│  │    ALU (Arithmetic Logic  │      │
│  │         Unit)             │      │
│  │  • Addition, Subtraction  │      │
│  │  • AND, OR, NOT, XOR      │      │
│  │  • Bit shifts, rotates    │      │
│  └───────────┬───────────────┘      │
│              ↓                       │
│  ┌─────────────────────┐            │
│  │ Registers (R0-R15)  │            │
│  │                     │            │
│  │ R0-R12: General use │            │
│  │ R13: Stack Pointer  │            │
│  │ R14: Link Register  │            │
│  │ R15: Program Counter│            │
│  └─────────────────────┘            │
└──────────────────────────────────────┘
```

### How Fast is 72 MHz?

```
72,000,000 cycles per second
= 1 cycle every 13.9 nanoseconds

Comparison:
- Human eye blink: ~100 milliseconds
- In that time, STM32 executes 7,200,000 instructions!

Motor control loop (100Hz):
- Runs every 10 milliseconds
- In 10ms, STM32 can execute 720,000 instructions
- More than enough for PID calculations!
```

---

## Memory Types Explained

### Flash Memory (256 KB)
- **Non-volatile**: Keeps data without power
- **Read mostly**: Written only during firmware updates
- **Stores**: Your compiled C program

```
Flash = A book
- Written once, read many times
- Permanent storage
- Contains the firmware code
```

### SRAM (48 KB)
- **Volatile**: Loses data when power off
- **Read/Write**: Fast access during runtime
- **Stores**: Variables, arrays, stack

```
SRAM = Whiteboard
- Easy to write and erase
- Temporary storage
- Fast access
```

---

## Exercise: Memory Calculation

**Scenario**: Your program uses:
- 180 KB for code (Flash)
- 10 KB for global variables (RAM)
- 5 KB for stack (RAM)

**Questions**:
1. How much Flash remains?
2. How much RAM remains?
3. Can you add a 20 KB array?

**Answers** (think first, then check):

<details>
<summary>Click for answers</summary>

1. Flash remaining: 256 - 180 = **76 KB**
2. RAM remaining: 48 - 10 - 5 = **33 KB**
3. 20 KB array: **Yes**, 33 KB > 20 KB

</details>

---

## Summary

- **Microcontroller** = Computer on a single chip (CPU + Memory + I/O)
- **STM32F103RCT6** = 72 MHz, 256KB Flash, 48KB RAM, 51 GPIO pins
- **Chosen for OrbiBot** = Fast enough, affordable, right peripherals
- **ARM Cortex-M3** = 32-bit processor, 72 million instructions/sec

---

## Next Lesson

[Part 0: Electronics Fundamentals](02-electronics-fundamentals.md) - Learn about voltage, current, and digital signals

---

*OrbiBot Firmware Study Guide*  
*Part 0 of 10*