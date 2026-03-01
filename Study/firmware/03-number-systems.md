# Part 0: Number Systems

**Duration**: 20 minutes  
**Prerequisites**: [02-electronics-fundamentals.md](02-electronics-fundamentals.md)

---

## Learning Objectives

After this lesson, you will understand:
- Decimal (base-10) numbers
- Binary (base-2) numbers
- Hexadecimal (base-16) numbers
- How to convert between them
- Why programmers use hexadecimal

---

## Decimal (Base-10)

The number system we use every day.

```
Digits: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

Example: 245

Breakdown:
  2 × 100 = 200
  4 × 10  =  40
  5 × 1   =   5
  ─────────────────
  Total   = 245
```

Each position is a power of 10:
```
Position:   2      1      0
Power:     10²    10¹    10⁰
Value:     100     10      1
```

---

## Binary (Base-2)

The language of computers. Only two digits: **0 and 1**

```
Each digit is called a "bit"

Example: 1011 (binary)

Breakdown:
  1 × 8  = 8    (2³)
  0 × 4  = 0    (2²)
  1 × 2  = 2    (2¹)
  1 × 1  = 1    (2⁰)
  ─────────────
  Total  = 11 (decimal)
```

### Binary Position Values

| Position | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|----------|---|---|---|---|---|---|---|---|
| Power | 2⁷ | 2⁶ | 2⁵ | 2⁴ | 2³ | 2² | 2¹ | 2⁰ |
| Value | 128 | 64 | 32 | 16 | 8 | 4 | 2 | 1 |

### Common Binary Values

| Binary | Decimal |
|--------|---------|
| 0000 | 0 |
| 0001 | 1 |
| 0010 | 2 |
| 0100 | 4 |
| 1000 | 8 |
| 1111 | 15 |
| 11111111 | 255 |

### Why Binary?

Computers use binary because:
- Electronic circuits have two states: ON (1) or OFF (0)
- 3.3V = 1, 0V = 0
- Simple and reliable

---

## Hexadecimal (Base-16)

A compact way to represent binary numbers.

```
Digits: 0-9, then A-F

Decimal:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
Hex:      0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
```

### Why Use Hexadecimal?

```
Binary:  11111111 11111111 11111111 11111111
          (32 characters, hard to read)

Hex:     0xFFFFFFFF
          (10 characters, much better!)

One hex digit = 4 binary digits (one "nibble")
```

### Hex to Binary Conversion

| Hex | Binary |
|-----|--------|
| 0 | 0000 |
| 1 | 0001 |
| 2 | 0010 |
| 4 | 0100 |
| 8 | 1000 |
| A | 1010 |
| F | 1111 |

**Example**: Convert 0xA5 to binary
```
A = 1010
5 = 0101
0xA5 = 10100101 (binary)
```

---

## Conversion Methods

### Binary to Decimal

**Method**: Add up the position values where there's a 1

```
Binary:  1 0 1 1 0 1 0 0
Value: 128 64 32 16 8 4 2 1
         ↑     ↑  ↑    ↑
         └─────┴──┴────┘
         128 + 32 + 16 + 4 = 180

Answer: 10110100 (binary) = 180 (decimal)
```

### Decimal to Binary

**Method**: Divide by 2, keep remainders

```
Convert 45 to binary:

45 ÷ 2 = 22 remainder 1 ↑
22 ÷ 2 = 11 remainder 0 ↑
11 ÷ 2 = 5  remainder 1 ↑
5  ÷ 2 = 2  remainder 1 ↑
2  ÷ 2 = 1  remainder 0 ↑
1  ÷ 2 = 0  remainder 1 ↑

Read remainders from bottom to top: 101101

Answer: 45 (decimal) = 00101101 (binary, 8-bit)
```

### Decimal to Hexadecimal

**Method**: Divide by 16, keep remainders

```
Convert 255 to hex:

255 ÷ 16 = 15 remainder 15 (F)
15  ÷ 16 = 0  remainder 15 (F)

Answer: 255 (decimal) = 0xFF (hexadecimal)
```

---

## In Firmware Code

### Common Patterns

```c
// Register addresses (always in hex)
#define GPIOA_BASE   0x40010800
#define TIM1_BASE    0x40012C00

// Bit masks
#define LED_PIN      0x20    // Pin 5 (bit 5)
#define ALL_PINS     0xFF    // All 8 pins

// Binary literals (GCC extension)
uint8_t pattern = 0b10101010;  // Binary
uint8_t mask    = 0xAA;        // Same value in hex
```

### Bitwise Operations

```c
uint8_t value = 0x0F;  // 00001111

// Set bit 4
value |= (1 << 4);     // 00001111 | 00010000 = 00011111 (0x1F)

// Clear bit 0
value &= ~(1 << 0);    // 00011111 & 11111110 = 00011110 (0x1E)

// Toggle bit 7
value ^= (1 << 7);     // 00011110 ^ 10000000 = 10011110 (0x9E)

// Check bit 3
if (value & (1 << 3)) {
    // Bit 3 is set
}
```

---

## Exercises

**Exercise 1**: Convert these binary to decimal
- a) 00001010 = ?
- b) 11110000 = ?
- c) 10101010 = ?

**Exercise 2**: Convert these decimal to binary (8-bit)
- a) 25 = ?
- b) 100 = ?
- c) 200 = ?

**Exercise 3**: Convert these hex to binary
- a) 0x3F = ?
- b) 0xA5 = ?
- c) 0xFF = ?

**Answers**:

<details>
<summary>Click for answers</summary>

**Exercise 1**:
- a) 00001010 = 8 + 2 = **10**
- b) 11110000 = 128 + 64 + 32 + 16 = **240**
- c) 10101010 = 128 + 32 + 8 + 2 = **170**

**Exercise 2**:
- a) 25 = **00011001**
- b) 100 = **01100100**
- c) 200 = **11001000**

**Exercise 3**:
- a) 0x3F = **00111111**
- b) 0xA5 = **10100101**
- c) 0xFF = **11111111**

</details>

---

## Summary

| System | Base | Digits | Used For |
|--------|------|--------|----------|
| Decimal | 10 | 0-9 | Human counting |
| Binary | 2 | 0,1 | Computer circuits |
| Hexadecimal | 16 | 0-9,A-F | Compact binary representation |

- **Binary**: Computer's native language
- **Hexadecimal**: Programmer's shorthand for binary
- **8 bits** = 1 byte = 2 hex digits

---

## Next Lesson

[04-memory-and-registers.md](04-memory-and-registers.md) - Memory types and register addressing

---

*OrbiBot Firmware Study Guide*  
*Part 0 of 10*