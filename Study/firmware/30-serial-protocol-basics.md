# Part 3: Serial Communication Protocol

**Duration**: 20 minutes  
**Prerequisites**: [23-orbibot-task-architecture.md](23-orbibot-task-architecture.md)

---

## Learning Objectives

After this lesson, you will understand:
- Why OrbiBot needs a communication protocol
- UART basics
- How firmware and ROS 2 communicate
- Protocol design principles

---

## Why Do We Need a Protocol?

### The Problem

```
Raspberry Pi (ROS 2) and STM32 need to talk to each other:
  - Pi sends: "Move forward at 0.5 m/s"
  - STM32 sends: "Current position is (1.2, 0.8, 0.0)"
  - Pi sends: "Stop motors"
  - STM32 sends: "Battery at 12.4V"

Without a protocol:
  - How do we know message boundaries?
  - How do we detect corruption?
  - How do we handle different message types?
```

### What a Protocol Provides

1. **Message Structure**: Where does one message end and next begin?
2. **Data Integrity**: Checksum to detect corruption
3. **Message Types**: Different commands and responses
4. **Error Handling**: What to do when things go wrong

---

## UART Communication Basics

### What is UART?

**UART** = Universal Asynchronous Receiver/Transmitter

```
Connection:
┌─────────┐                ┌─────────┐
│   Pi    │─── TX ────────→│  STM32  │
│ (USB)   │←── RX ─────────│ (UART1) │
└─────────┘                └─────────┘

TX = Transmit (sending)
RX = Receive (getting)

Note: TX of one connects to RX of other!
```

### UART Parameters (OrbiBot)

| Parameter | Value | Meaning |
|-----------|-------|---------|
| Baud Rate | 115200 | Bits per second |
| Data Bits | 8 | Bytes have 8 bits |
| Stop Bits | 1 | End of byte marker |
| Parity | None | No error checking (we use checksum) |

### Data Rate

```
115200 baud = 115200 bits/second
            = 14400 bytes/second (115200 / 8)
            = 14.4 KB/s

For comparison:
  - USB 2.0: 480 Mbps (much faster)
  - But UART is simple and reliable for robot control
```

---

## OrbiBot Protocol Overview

### Protocol Design

```
Packet Format:
[0xFF][Device_ID][Length][Function][Data...][Checksum]

Byte 0: 0xFF      - Header (start marker)
Byte 1: Device ID - 0xFC (Pi→STM32) or 0xFB (STM32→Pi)
Byte 2: Length    - Total packet length minus 2
Byte 3: Function  - What command/data
Byte 4-N: Data    - Command parameters or sensor data
Last Byte: Checksum - Error detection
```

### Why This Design?

| Feature | Purpose |
|---------|---------|
| 0xFF Header | Easy to find start of packet |
| Device ID | Know which direction message flows |
| Length | Know when packet ends |
| Function Code | What type of message |
| Checksum | Detect corrupted data |

---

## Message Types

### From Raspberry Pi to STM32 (Commands)

| Function Code | Name | Purpose |
|---------------|------|---------|
| 0x01 | AUTO_REPORT | Enable/disable data streaming |
| 0x02 | BEEP | Sound the buzzer |
| 0x12 | MOTION | Set robot velocity (Vx, Vy, ω) |
| 0x13 | SET_MOTOR_PID | Change motor PID gains |
| 0x14 | SET_YAW_PID | Change yaw PID gains |
| 0x09 | RESET_ODOM | Reset position to zero |
| 0x51 | VERSION | Request firmware version |

### From STM32 to Raspberry Pi (Data)

| Function Code | Name | Purpose |
|---------------|------|---------|
| 0x0A | REPORT_SPEED | Current velocity + battery |
| 0x0C | REPORT_IMU_ATT | Roll, pitch, yaw angles |
| 0x0D | REPORT_ENCODER | Wheel encoder counts |
| 0x0E | REPORT_ICM_RAW | Raw IMU sensor data |
| 0x15 | REPORT_ODOM | Position (x, y, θ) |

---

## Example: Motion Command

### Pi Sends: "Move Forward at 0.3 m/s"

```
Packet Construction:

[0xFF][0xFC][0x09][0x12][0x00][0x2C][0x01][0xF4][0x00][0x00][0x00][0x00][0xChecksum]

Breakdown:
0xFF       - Header
0xFC       - Device ID (Pi to STM32)
0x09       - Length (9 bytes after this)
0x12       - Function (MOTION command)
0x00       - Car type (not used)
0x2C 0x01  - Vx = 300 mm/s (little-endian: 0x012C = 300)
0xF4 0x01  - Vy = 500 mm/s (little-endian) → Actually inverted in protocol
0x00 0x00  - Vz = 0 mrad/s
0xChecksum - Calculated sum

Result: Robot moves forward at 0.3 m/s
```

### STM32 Responds: Auto-Report Data

```
When auto-report enabled, STM32 sends every 50ms:

[0xFF][0xFB][0x07][0x0A][Vx_lo][Vx_hi][Vy_lo][Vy_hi][Vz_lo][Vz_hi][Battery][Checksum]

Breakdown:
0xFF       - Header
0xFB       - Device ID (STM32 to Pi)
0x07       - Length (7 bytes)
0x0A       - Function (REPORT_SPEED)
Vx_lo/hi   - Measured X velocity (mm/s)
Vy_lo/hi   - Measured Y velocity (mm/s)  
Vz_lo/hi   - Measured rotation (mrad/s)
Battery    - Voltage × 10 (e.g., 124 = 12.4V)
Checksum   - Error detection
```

---

## Checksum Calculation

### Why Checksum?

```
Without checksum:
  [0xFF][0xFC][0x03][0x12][0x00][0x00][0x00]

If noise corrupts byte:
  [0xFF][0xFC][0x03][0x**FF**][0x00][0x00][0x00] ← Wrong command!

With checksum:
  [0xFF][0xFC][0x03][0x12][0x00][0x00][0x00][0x11]
  Sum = 0xFC + 0x03 + 0x12 + 0x00 + 0x00 + 0x00 = 0x111

If corrupted, checksum fails → Discard packet
```

### Checksum Formula

```c
uint8_t calculate_checksum(uint8_t *data, uint8_t length) {
    uint16_t sum = 0;
    
    // Sum from Device ID (index 1) to last data byte
    for (uint8_t i = 1; i < length - 1; i++) {
        sum += data[i];
    }
    
    return (uint8_t)(sum & 0xFF);  // Keep only low 8 bits
}
```

### Example Calculation

```
Packet: [0xFF][0xFC][0x03][0x12][0x00][0x00][0x00][Checksum]

Sum = 0xFC + 0x03 + 0x12 + 0x00 + 0x00 + 0x00
    = 252 + 3 + 18 + 0 + 0 + 0
    = 273
    = 0x111

Checksum = 0x111 & 0xFF = 0x11

Final packet: [0xFF][0xFC][0x03][0x12][0x00][0x00][0x00][0x11]
```

---

## State Machine Parsing

### Why State Machine?

```
Receiving bytes one at a time from UART:
  Byte 0: 0xFF ← Is this header?
  Byte 1: 0xFC ← Is this valid device ID?
  Byte 2: 0x09 ← What's the length?
  Byte 3: 0x12 ← What's the function?
  ...

Need to track where we are in the packet!
```

### State Machine Diagram

```
States:
  1. WAIT_HEADER    → Looking for 0xFF
  2. WAIT_DEVICE    → Got header, check device ID
  3. WAIT_LENGTH    → Got device ID, read length
  4. READ_DATA      → Reading payload bytes
  5. CHECKSUM       → Verify checksum
  6. PROCESS        → Execute command

Transitions:
  WAIT_HEADER --(0xFF)--> WAIT_DEVICE
  WAIT_DEVICE --(0xFC)--> WAIT_LENGTH
  WAIT_LENGTH --(valid)--> READ_DATA
  READ_DATA --(complete)--> CHECKSUM
  CHECKSUM --(valid)--> PROCESS
  CHECKSUM --(invalid)--> WAIT_HEADER (reset)
  Any state --(timeout/error)--> WAIT_HEADER (reset)
```

---

## Protocol in Firmware

### From `protocol.c`:

```c
// Receive state machine
typedef enum {
    RX_STATE_WAIT_HEADER,
    RX_STATE_WAIT_DEVICE,
    RX_STATE_WAIT_LENGTH,
    RX_STATE_READ_DATA
} rx_state_t;

// Called for each received byte (from UART ISR)
void protocol_receive_byte(uint8_t byte) {
    switch (g_rx_state) {
        case RX_STATE_WAIT_HEADER:
            if (byte == 0xFF) {
                g_rx_buffer[0] = byte;
                g_rx_index = 1;
                g_rx_state = RX_STATE_WAIT_DEVICE;
            }
            break;
            
        case RX_STATE_WAIT_DEVICE:
            if (byte == 0xFC) {  // Valid device ID
                g_rx_buffer[1] = byte;
                g_rx_index = 2;
                g_rx_state = RX_STATE_WAIT_LENGTH;
            } else {
                g_rx_state = RX_STATE_WAIT_HEADER;  // Reset
            }
            break;
            
        // ... more states ...
    }
}
```

---

## Exercise: Parse a Packet

**Given**: Received bytes one at a time:
```
0xFF, 0xFC, 0x03, 0x12, 0x00, 0x00, 0x00, 0x11
```

**Questions**:
1. What state are we in after each byte?
2. What's the function code?
3. What's the command?
4. Is checksum valid?

**Answers**:

<details>
<summary>Click for answer</summary>

```
Byte 0 (0xFF): WAIT_HEADER → WAIT_DEVICE
Byte 1 (0xFC): WAIT_DEVICE → WAIT_LENGTH
Byte 2 (0x03): WAIT_LENGTH → READ_DATA (length = 3)
Byte 3 (0x12): READ_DATA (function = MOTION)
Byte 4 (0x00): READ_DATA (data[0] = car type)
Byte 5 (0x00): READ_DATA (data[1] = Vx_lo)
Byte 6 (0x00): READ_DATA (data[2] = Vx_hi)
Byte 7 (0x11): CHECKSUM → PROCESS

Function: 0x12 = MOTION (move robot)
Command: Stop (all velocities zero)
Checksum: 0xFC + 0x03 + 0x12 + 0x00 + 0x00 + 0x00 = 0x111 → 0x11 ✓ VALID
```

</details>

---

## Summary

- **Protocol** = Rules for communication between devices
- **UART** = Serial communication at 115200 baud
- **Packet structure**: Header + Device ID + Length + Function + Data + Checksum
- **Checksum** = Error detection
- **State machine** = Parse bytes as they arrive
- **Two-way communication**: Pi sends commands, STM32 sends data

---

## Next Lesson

[31-packet-structure.md](31-packet-structure.md) - Detailed packet format and all commands

---

*OrbiBot Firmware Study Guide*  
*Part 3 of 10*