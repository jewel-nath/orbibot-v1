---
title: "Part 0: Electronics Fundamentals"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "25 minutes"
tags:
  - learn
  - firmware
---

# Part 0: Electronics Fundamentals

**Duration**: 25 minutes  
**Prerequisites**: [[01-microcontroller-basics]]

---

## Learning Objectives

After this lesson, you will understand:
- Voltage, current, and resistance
- Digital signals (HIGH/LOW)
- Basic circuit concepts
- How these apply to OrbiBot

---

## Voltage, Current, and Resistance

### Voltage (V) - Electrical Pressure

**Definition**: The "pressure" that pushes electric charges through a circuit.

**Analogy - Water System**:
```
Voltage = Water Pressure
- Higher pressure = water flows faster
- Higher voltage = electrons flow more

Examples:
- AA Battery: 1.5V (low pressure)
- USB Power: 5V
- OrbiBot 12V battery: 12V (higher pressure)
- STM32 GPIO: 3.3V (logic level)
```

### Current (I) - Flow Rate

**Definition**: The rate of electron flow through a circuit.

**Analogy - Water System**:
```
Current = Water Flow Rate
- More flow = more water per second
- More current = more electrons per second

Unit: Ampere (A), milliampere (mA)

Examples:
- LED: 20mA (0.02A)
- STM32 chip: 50mA
- OrbiBot motor: 1-2A
```

### Resistance (R) - Opposition to Flow

**Definition**: How much a material opposes electric current.

**Analogy - Water System**:
```
Resistance = Pipe Narrowing
- Narrow pipe = harder to flow = higher resistance
- Wide pipe = easier to flow = lower resistance

Unit: Ohm (Ω)

Examples:
- Wire: near 0Ω (very low)
- LED current-limiting resistor: 220Ω
- Pull-up resistor: 10kΩ (10,000Ω)
```

### Ohm's Law

The fundamental relationship:

```
V = I × R

Voltage = Current × Resistance

Rearranged:
I = V / R    (Current = Voltage / Resistance)
R = V / I    (Resistance = Voltage / Current)
```

**Practical Example**:
```
You have:
- 3.3V (STM32 GPIO voltage)
- LED that needs 20mA (0.02A)
- What resistor do you need?

R = V / I = 3.3V / 0.02A = 165Ω

Use 220Ω resistor (standard value, slightly less current = safer)
```

---

## Digital Signals

Microcontrollers understand only two states:

### HIGH (Logic 1)
- **Voltage**: 3.3V (for STM32)
- **Meaning**: ON, TRUE, YES, Active
- **Visual**: ████ (solid line)

### LOW (Logic 0)
- **Voltage**: 0V (GND)
- **Meaning**: OFF, FALSE, NO, Inactive
- **Visual**: ____ (flat line)

### Digital Signal Example

```
Time →

3.3V ─┐     ┌────┐        ┌───┐
      │     │    │        │   │
      └─────┘    └────────┘   └─── 0V

State: ON    OFF   ON      OFF  ON

In code:
  GPIO_SetBits(GPIOA, GPIO_Pin_0);    // HIGH
  GPIO_ResetBits(GPIOA, GPIO_Pin_0);  // LOW
```

---

## OrbiBot Voltage Levels

### System Voltages

| Component | Voltage | Notes |
|-----------|---------|-------|
| STM32 MCU | 3.3V | Core logic level |
| Motors | 12V | Powered by battery |
| USB | 5V | From Raspberry Pi |
| IMU sensor | 3.3V | SPI communication |
| Encoders | 3.3V | Quadrature signals |

### Voltage Dividers (for Battery Monitoring)

The STM32 ADC can only measure up to 3.3V, but the battery is 12V. A **voltage divider** scales it down:

```
Battery (12V) ───[10kΩ]───┬───[3.3kΩ]─── GND
                          │
                      To ADC
                          │
                    Measures ~3.0V
                    (when battery = 12V)

Formula: Vout = Vin × (R2 / (R1 + R2))
         Vout = 12V × (3.3k / (10k + 3.3k))
         Vout = 12V × 0.248 = 2.98V
```

---

## GPIO Pin States

### Output Modes

```c
// Set pin HIGH (3.3V)
GPIO_SetBits(GPIOA, GPIO_Pin_5);    // LED ON

// Set pin LOW (0V)
GPIO_ResetBits(GPIOA, GPIO_Pin_5);  // LED OFF
```

### Input Modes

```c
// Read pin state
uint8_t state = GPIO_ReadInputDataBit(GPIOB, GPIO_Pin_0);

if (state == 1) {
    // Pin is HIGH (3.3V)
} else {
    // Pin is LOW (0V)
}
```

---

## Pull-Up and Pull-Down Resistors

### Why Needed?

When a button is NOT pressed, the pin is "floating" - it picks up electrical noise.

```
Floating Pin (BAD):
     Button
   ┌──/ /──┐
   │       │
   │    ┌──┴──┐
GND    │ Pin │  ??? (random noise)
       └──┬──┘
          

With Pull-Up (GOOD):
     Button
   ┌──/ /──┐
   │       │
3.3V──[10k]─┤    Pin is HIGH when button NOT pressed
            ├──→ Pin is LOW when button pressed
       ┌────┤
       │ Pin│
       └────┘
```

### Types

| Type | Default State | Activated State |
|------|---------------|-----------------|
| Pull-Up | HIGH (3.3V) | LOW when button pressed |
| Pull-Down | LOW (0V) | HIGH when button pressed |

---

## Exercise: Circuit Analysis

**Question 1**: An LED has 2V forward voltage and needs 15mA. You have 5V supply. What resistor do you need?

**Question 2**: Why does OrbiBot use 3.3V for logic but 12V for motors?

**Answers**:

<details>
<summary>Click for answers</summary>

**Q1**:
```
Voltage across resistor = 5V - 2V = 3V
R = V / I = 3V / 0.015A = 200Ω
Use 220Ω (standard value)
```

**Q2**:
```
3.3V for logic:
- STM32 operates at 3.3V
- Lower voltage = less power, less heat
- Sufficient for digital signals

12V for motors:
- Motors need more power (P = V × I)
- Higher voltage = more torque
- 12V is standard for robot motors
```

</details>

---

## Summary

- **Voltage** = Electrical pressure (V)
- **Current** = Flow rate (A)
- **Resistance** = Opposition to flow (Ω)
- **Ohm's Law**: V = I × R
- **Digital signals**: Only HIGH (3.3V) or LOW (0V)
- **Pull-up/down**: Keep pins in known state

---

## Next Lesson

[[03-number-systems]] - Binary, hexadecimal, and decimal number systems

---

*OrbiBot Firmware Study Guide*  
*Part 0 of 10*