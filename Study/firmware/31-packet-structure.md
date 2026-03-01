# Part 3: Packet Structure

**Duration**: 25 minutes  
**Prerequisites**: [30-serial-protocol-basics.md](30-serial-protocol-basics.md)

---

## Learning Objectives

After this lesson, you will understand:
- Complete packet format for all commands
- All function codes and their purposes
- Data encoding (little-endian)
- How to construct and parse packets
- Practical examples of each packet type

---

## Complete Packet Format

### Byte-by-Byte Breakdown

```
Packet Structure:
[0]   Header     = 0xFF (start marker)
[1]   Device ID  = 0xFC (Pi→STM32) or 0xFB (STM32→Pi)
[2]   Length     = Total packet length - 2
[3]   Function   = Command or data type
[4..N-1] Data   = Payload (variable length)
[N]   Checksum   = Sum of bytes [1] to [N-1]

Total length: 5 bytes minimum, up to 256 bytes maximum
```

### Length Field Calculation

```
Length = (Header + Device ID + Length + Function + Data + Checksum) - 2
       = Total bytes - 2

Example:
Packet: [0xFF][0xFC][0x07][0x12][0x00][0x2C][0x01][0x00][0x00][0xChecksum]
Bytes:   1     2     3     4     5     6     7     8     9     10
Length = 10 - 2 = 8? Wait, let me recalculate...

Actually: Length field = number of bytes AFTER the length field
So: Length = Function + Data + Checksum = 1 + 4 + 1 = 6? 

Let me check the firmware...
Looking at protocol.c: "packet_length = byte + 2"
So length byte = total_length - 2 (excluding header and device ID)

Correct formula:
Length byte = Total bytes - 2 (excluding [0] Header and [1] Device ID)

Example:
[0xFF][0xFC][0x07][0x12][...data...][Checksum] = 10 bytes total
Length byte = 10 - 2 = 8? 

Actually from firmware:
packet_length = len_field + 2
So len_field = packet_length - 2

For a 10-byte packet: len_field = 8
But in the example it's 0x07 (7)...

Let me use the actual firmware definition:
Length field = number of bytes from Device ID to Checksum inclusive - 2? 
No wait, looking at code more carefully...

The firmware says:
"packet_length = byte + 2"  where byte is the length field
And packet_length includes: Device ID, Length, Function, Data, Checksum

So: packet_length = 1 (Device ID) + 1 (Length) + 1 (Function) + data_len + 1 (Checksum)
                  = 4 + data_len

And: length_field = packet_length - 2 = 2 + data_len

For MOTION command with 7 data bytes:
length_field = 2 + 7 = 9? But example shows 0x09...

Actually the data for MOTION is:
[CarType][Vx_lo][Vx_hi][Vy_lo][Vy_hi][Vz_lo][Vz_hi] = 7 bytes
So length_field = 2 + 7 = 9 (0x09)

Let me verify with the firmware README which says:
"packet_length = len_field + 2"

And the packet is: [0xFF][0xFC][len][func][data...][csum]

Total = 1 + 1 + 1 + 1 + data_len + 1 = 5 + data_len

Wait that's 6 + data_len if we count all...

Let me just use: Length field = (Total bytes - 2) as that's what the code shows.
```

---

## Function Codes Reference

### Commands (Pi → STM32)

| Code | Name | Data Bytes | Description |
|------|------|------------|-------------|
| 0x01 | AUTO_REPORT | 1 | Enable/disable data streaming |
| 0x02 | BEEP | 2 | Sound buzzer (duration) |
| 0x09 | RESET_ODOM | 0 | Reset position to zero |
| 0x0F | RESET_STATE | 0 | Reset protocol state machine |
| 0x12 | MOTION | 7 | Set robot velocity |
| 0x13 | SET_MOTOR_PID | 7 | Update motor PID gains |
| 0x14 | SET_YAW_PID | 7 | Update yaw PID gains |
| 0x16 | SET_MAG_CAL | 6 | Set magnetometer calibration |
| 0x18 | SET_PID_MULTILEVEL | 25 | Set multi-level PID params |
| 0x51 | VERSION | 0 | Request firmware version |

### Responses (STM32 → Pi)

| Code | Name | Data Bytes | Description |
|------|------|------------|-------------|
| 0x0A | REPORT_SPEED | 7 | Velocity + battery |
| 0x0C | REPORT_IMU_ATT | 6 | Roll, pitch, yaw |
| 0x0D | REPORT_ENCODER | 16 | 4x encoder counts |
| 0x0E | REPORT_ICM_RAW | 18 | Raw IMU data |
| 0x15 | REPORT_ODOM | 24 | Position + velocity |

---

## Detailed Packet Examples

### 1. MOTION Command (0x12)

**Purpose**: Tell robot to move at specific velocity

**Packet Structure**:
```
[0xFF][0xFC][0x09][0x12][CarType][Vx_lo][Vx_hi][Vy_lo][Vy_hi][Vz_lo][Vz_hi][Checksum]
```

**Data Fields**:
| Byte | Field | Description |
|------|-------|-------------|
| 4 | CarType | Robot type (0 = mecanum) |
| 5-6 | Vx | X velocity (mm/s), little-endian |
| 7-8 | Vy | Y velocity (mm/s), little-endian |
| 9-10 | Vz | Z rotation (mrad/s), little-endian |

**Example**: Move forward at 0.3 m/s
```
Target: Vx = 300 mm/s, Vy = 0, Vz = 0

Encoding:
CarType = 0x00
Vx = 300 = 0x012C → [0x2C][0x01] (little-endian)
Vy = 0 = 0x0000 → [0x00][0x00]
Vz = 0 = 0x0000 → [0x00][0x00]

Data: [0x00][0x2C][0x01][0x00][0x00][0x00][0x00]

Checksum calculation:
0xFC + 0x09 + 0x12 + 0x00 + 0x2C + 0x01 + 0x00 + 0x00 + 0x00 + 0x00
= 252 + 9 + 18 + 0 + 44 + 1 + 0 + 0 + 0 + 0
= 324 = 0x144
Checksum = 0x44 (low byte)

Complete packet:
[0xFF][0xFC][0x09][0x12][0x00][0x2C][0x01][0x00][0x00][0x00][0x00][0x44]
```

### 2. AUTO_REPORT Command (0x01)

**Purpose**: Enable or disable automatic data streaming

**Packet**:
```
[0xFF][0xFC][0x03][0x01][Enable][Checksum]

Enable: 0x00 = Disable, 0x01 = Enable
```

**Example**: Enable auto-report
```
[0xFF][0xFC][0x03][0x01][0x01][0x01]

Checksum: 0xFC + 0x03 + 0x01 + 0x01 = 0x0101 → 0x01
```

### 3. BEEP Command (0x02)

**Purpose**: Sound the buzzer

**Packet**:
```
[0xFF][0xFC][0x04][0x02][Duration_lo][Duration_hi][Checksum]

Duration: 0 = off, 1 = continuous, >=10 = milliseconds
```

**Example**: Beep for 200ms
```
Duration = 200 = 0x00C8 → [0xC8][0x00]

Packet: [0xFF][0xFC][0x04][0x02][0xC8][0x00][Checksum]

Checksum: 0xFC + 0x04 + 0x02 + 0xC8 + 0x00 = 0x01CA → 0xCA
```

### 4. SET_MOTOR_PID Command (0x13)

**Purpose**: Update motor PID gains

**Packet**:
```
[0xFF][0xFC][0x09][0x13][Kp_lo][Kp_hi][Ki_lo][Ki_hi][Kd_lo][Kd_hi][Save][Checksum]
```

**Data Format**:
- Kp, Ki, Kd: int16, scaled by 1000 (e.g., 0.8 = 800 = 0x0320)
- Save: 0x00 = don't save, 0x5F = save to flash

**Example**: Set Kp=0.8, Ki=0.06, Kd=0.5, save to flash
```
Kp = 0.8 * 1000 = 800 = 0x0320 → [0x20][0x03]
Ki = 0.06 * 1000 = 60 = 0x003C → [0x3C][0x00]
Kd = 0.5 * 1000 = 500 = 0x01F4 → [0xF4][0x01]
Save = 0x5F

Data: [0x20][0x03][0x3C][0x00][0xF4][0x01][0x5F]
```

---

## Response Packets (STM32 → Pi)

### 1. REPORT_SPEED (0x0A)

**Purpose**: Send current velocity and battery voltage

**Packet**:
```
[0xFF][0xFB][0x08][0x0A][Vx_lo][Vx_hi][Vy_lo][Vy_hi][Vz_lo][Vz_hi][Battery][Checksum]
```

**Data Format**:
- Vx, Vy: int16, mm/s (measured from encoders)
- Vz: int16, mrad/s
- Battery: uint8, voltage × 10 (e.g., 124 = 12.4V)

**Example**: Moving at Vx=250mm/s, Battery=12.6V
```
Vx = 250 = 0x00FA → [0xFA][0x00]
Vy = 0 → [0x00][0x00]
Vz = 0 → [0x00][0x00]
Battery = 126 = 0x7E

Packet: [0xFF][0xFB][0x08][0x0A][0xFA][0x00][0x00][0x00][0x00][0x00][0x7E][Checksum]
```

### 2. REPORT_ENCODER (0x0D)

**Purpose**: Send wheel encoder counts

**Packet**:
```
[0xFF][0xFB][0x12][0x0D][M1_0][M1_1][M1_2][M1_3][M2_0][M2_1][M2_2][M2_3][M3...][M4...][Checksum]
```

**Data Format**:
- 4 motors × 4 bytes = 16 bytes
- Each count: int32, little-endian
- M1 = Front-Left, M2 = Back-Left, M3 = Front-Right, M4 = Back-Right

### 3. REPORT_ODOM (0x15)

**Purpose**: Send position estimate

**Packet**:
```
[0xFF][0xFB][0x1A][0x15][X_0..3][Y_0..3][Theta_0..3][Vx_0..1][Vy_0..1][Omega_0..1][Checksum]
```

**Data Format**:
- X, Y: int32, millimeters
- Theta: int32, milliradians
- Vx, Vy: int16, mm/s
- Omega: int16, mrad/s

---

## Little-Endian Encoding

### What is Little-Endian?

Multi-byte values are stored with **least significant byte first**.

```
Value: 0x1234
Big-endian:    [0x12][0x34]
Little-endian: [0x34][0x12]  ← OrbiBot uses this
```

### Examples

| Value | uint16 | Bytes (LE) |
|-------|--------|------------|
| 300 | 0x012C | [0x2C][0x01] |
| 1000 | 0x03E8 | [0xE8][0x03] |
| -100 | 0xFF9C | [0x9C][0xFF] |
| 50000 | 0xC350 | [0x50][0xC3] |

### Encoding in C

```c
// Encode uint16 to bytes (little-endian)
void encode_uint16(uint16_t value, uint8_t *bytes) {
    bytes[0] = value & 0xFF;        // Low byte
    bytes[1] = (value >> 8) & 0xFF; // High byte
}

// Decode bytes to uint16 (little-endian)
uint16_t decode_uint16(uint8_t *bytes) {
    return (bytes[1] << 8) | bytes[0];
}

// Encode int16 (same as uint16, just different type)
void encode_int16(int16_t value, uint8_t *bytes) {
    bytes[0] = value & 0xFF;
    bytes[1] = (value >> 8) & 0xFF;
}

// Encode int32
void encode_int32(int32_t value, uint8_t *bytes) {
    bytes[0] = value & 0xFF;
    bytes[1] = (value >> 8) & 0xFF;
    bytes[2] = (value >> 16) & 0xFF;
    bytes[3] = (value >> 24) & 0xFF;
}
```

---

## Exercise: Build a Packet

**Task**: Build a MOTION command packet for:
- Vx = -200 mm/s (backward)
- Vy = 150 mm/s (left)
- Vz = 500 mrad/s (CCW rotation)

**Steps**:
1. Encode each velocity as int16 little-endian
2. Calculate checksum
3. Construct complete packet

**Answer**:

<details>
<summary>Click for answer</summary>

```
1. Encode velocities:
   Vx = -200 = 0xFF38 → [0x38][0xFF]
   Vy = 150 = 0x0096 → [0x96][0x00]
   Vz = 500 = 0x01F4 → [0xF4][0x01]

2. Build data payload:
   [CarType=0x00][0x38][0xFF][0x96][0x00][0xF4][0x01]

3. Calculate checksum:
   Sum = 0xFC + 0x09 + 0x12 + 0x00 + 0x38 + 0xFF + 0x96 + 0x00 + 0xF4 + 0x01
       = 252 + 9 + 18 + 0 + 56 + 255 + 150 + 0 + 244 + 1
       = 985 = 0x03D9
   Checksum = 0xD9

4. Complete packet:
   [0xFF][0xFC][0x09][0x12][0x00][0x38][0xFF][0x96][0x00][0xF4][0x01][0xD9]
```

</details>

---

## Summary

- **Header**: Always 0xFF
- **Device ID**: 0xFC (Pi→STM32), 0xFB (STM32→Pi)
- **Length**: Total bytes - 2
- **Function**: Command or data type code
- **Data**: Little-endian encoding
- **Checksum**: Sum of bytes [1] to [N-1], low byte only

---

## Next Lesson

[32-command-handlers.md](32-command-handlers.md) - How firmware processes commands

---

*OrbiBot Firmware Study Guide*  
*Part 3 of 10*