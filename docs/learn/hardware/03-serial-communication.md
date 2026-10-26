# 03 - Serial Communication

**Understanding binary protocols and packet structures**

---

## 🎯 Learning Objectives

After reading this, you will understand:
- What serial communication is
- Binary vs text protocols
- The OrbiBot packet structure
- How data is encoded and decoded
- Checksums for error detection

---

## 📞 What is Serial Communication?

### Definition

**Serial** = Data sent one bit at a time, sequentially.

### Real-World Analogy: Morse Code

```
Morse Code (Serial):
  • One signal at a time
  • Dot-dot-dash = "A"
  • Slow but reliable over long distances

Parallel Communication (Modern Computers):
  • Multiple signals simultaneously
  • 8 wires for 1 byte at once
  • Fast but complex wiring
```

### Serial Port Settings

| Parameter | OrbiBot Value | Meaning |
|-----------|---------------|---------|
| **Port** | `/dev/motordriver` | Device file path |
| **Baud Rate** | 115200 | Bits per second |
| **Data Bits** | 8 | Bits per byte |
| **Stop Bits** | 1 | End-of-byte marker |
| **Parity** | None | No error checking bit |

**115200 baud** = ~14.4 KB/s = Fast enough for robot control!

---

## 📦 Binary vs Text Protocols

### Text Protocol Example (HTTP)

```
GET /index.html HTTP/1.1\r\n
Host: example.com\r\n
\r\n

Human-readable but:
  - Takes more bytes
  - Slower to parse
  - More CPU intensive
```

### Binary Protocol Example (OrbiBot)

```
[0xFF, 0xFC, 0x08, 0x12, 0xE8, 0x03, 0x00, 0x00, 0x00, 0x00, 0xXX]

Machine-readable:
  - Compact (fewer bytes)
  - Fast to parse
  - Less CPU usage
```

### Why Binary for Robots?

```
✅ Speed: Less data to send
✅ Efficiency: Fast parsing on microcontroller
✅ Deterministic: Fixed packet sizes
✅ Real-time: Predictable timing

Text protocols (JSON, XML):
  ❌ Variable length
  ❌ Parsing overhead
  ❌ More memory needed
```

---

## 🔧 OrbiBot Packet Structure

### The Protocol Format

```
┌─────────────────────────────────────────────────────────────┐
│                     PACKET FORMAT                            │
├────────┬────────┬────────┬────────┬──────────┬──────────────┤
│ Header │Device  │ Length │ Function│  Data    │  Checksum    │
│  (1B)  │ ID (1B)│  (1B)  │  (1B)   │ (N bytes)│    (1B)      │
├────────┼────────┼────────┼────────┼──────────┼──────────────┤
│ 0xFF   │ 0xFC   │ 0x08   │ 0x12   │ [data]   │ Calculated   │
└────────┴────────┴────────┴────────┴──────────┴──────────────┘
```

### Field Descriptions

| Field | Bytes | Value | Purpose |
|-------|-------|-------|---------|
| **Header** | 1 | `0xFF` | Start of packet marker |
| **Device ID** | 1 | `0xFC` | Identifies ROSMaster board |
| **Length** | 1 | Variable | Total bytes after header |
| **Function** | 1 | Variable | Command type |
| **Data** | N | Variable | Payload (depends on function) |
| **Checksum** | 1 | Calculated | Error detection |

---

## 📝 Function Codes

### Common Commands

| Code | Name | Description |
|------|------|-------------|
| `0x01` | AUTO_REPORT | Enable/disable auto data transmission |
| `0x02` | BEEP | Control buzzer |
| `0x09` | RESET_ODOM | Reset odometry to zero |
| `0x12` | MOTION | Set robot velocity |
| `0x13` | SET_MOTOR_PID | Configure motor PID |
| `0x14` | SET_YAW_PID | Configure yaw PID |
| `0x15` | REPORT_ODOM | Request odometry data |

### Data Report Functions

| Code | Name | Data Content |
|------|------|--------------|
| `0x0A` | SPEED | Battery + velocities |
| `0x0C` | IMU_ATT | Roll, pitch, yaw angles |
| `0x0D` | ENCODER | 4 motor encoder counts |
| `0x0E` | ICM_RAW | Raw IMU sensor data |
| `0x15` | ODOM | Position + velocity |

---

## 🔨 Example: Motion Command Packet

### Scenario: Move Forward at 0.5 m/s

```
Command: set_car_motion(0.5, 0.0, 0.0)
          vx=0.5, vy=0.0, vz=0.0 m/s
```

### Step-by-Step Encoding

```
Step 1: Convert to mm/s (multiply by 1000)
  vx = 0.5 × 1000 = 500 mm/s
  vy = 0.0 × 1000 = 0 mm/s
  vz = 0.0 × 1000 = 0 mm/s

Step 2: Pack into 16-bit integers
  500 = 0x01F4 → bytes: [0xF4, 0x01] (little-endian)
  0   = 0x0000 → bytes: [0x00, 0x00]
  0   = 0x0000 → bytes: [0x00, 0x00]

Step 3: Build packet
  [0xFF,                    // Header
   0xFC,                    // Device ID
   0x0B,                    // Length (11 bytes total - 1)
   0x12,                    // Function (MOTION)
   0x07,                    // Car type (OrbiBot)
   0xF4, 0x01,              // vx (500 mm/s)
   0x00, 0x00,              // vy (0 mm/s)
   0x00, 0x00,              // vz (0 rad/s * 1000)
   0xXX]                    // Checksum (calculated)

Step 4: Calculate checksum
  Sum: 0xFC + 0x0B + 0x12 + 0x07 + 0xF4 + 0x01 + 0x00 + 0x00 + 0x00 + 0x00
     = 0x0205
  Checksum = 0x205 & 0xFF = 0x05

Final packet:
  [0xFF, 0xFC, 0x0B, 0x12, 0x07, 0xF4, 0x01, 0x00, 0x00, 0x00, 0x00, 0x05]
```

---

## 🧮 Checksum Calculation

### Why Checksums?

```
Purpose: Detect corrupted data

Scenario:
  Packet gets corrupted on wire
  [0xFF, 0xFC, 0x0B, 0x12, ...] 
              ↓ corruption
  [0xFF, 0xFC, 0x0B, 0x92, ...] ← wrong function!

Without checksum: Robot does wrong thing!
With checksum: Error detected, packet ignored
```

### OrbiBot Checksum Formula

```python
def calculate_checksum(packet):
    """
    packet = [device_id, length, function, data...]
    """
    # Sum all bytes
    total = sum(packet)
    
    # Add complement constant
    total += (257 - 0xFC)  # 257 - device_id
    
    # Take low byte only
    checksum = total & 0xFF
    
    return checksum
```

### Example Checksum Calculation

```
Packet without checksum:
  [0xFC, 0x0B, 0x12, 0x07, 0xF4, 0x01, 0x00, 0x00, 0x00, 0x00]

Sum calculation:
  0xFC = 252
  0x0B = 11
  0x12 = 18
  0x07 = 7
  0xF4 = 244
  0x01 = 1
  0x00 = 0
  0x00 = 0
  0x00 = 0
  0x00 = 0
  ------
  Sum = 533
  
  + Complement (257 - 252 = 5)
  Total = 538 = 0x21A
  
  checksum = 0x21A & 0xFF = 0x1A
```

---

## 📥 Receiving Data: Parsing Packets

### State Machine Approach

```python
# Simplified parsing logic
def parse_serial_data(byte):
    global state, packet_buffer
    
    if state == "WAIT_HEADER":
        if byte == 0xFF:
            packet_buffer = [byte]
            state = "WAIT_DEVICE_ID"
    
    elif state == "WAIT_DEVICE_ID":
        if byte == 0xFC:
            packet_buffer.append(byte)
            state = "WAIT_LENGTH"
        else:
            state = "WAIT_HEADER"  # Invalid, restart
    
    elif state == "WAIT_LENGTH":
        length = byte
        packet_buffer.append(byte)
        bytes_remaining = length - 2  # Length includes type + data
        state = "READ_DATA"
    
    elif state == "READ_DATA":
        packet_buffer.append(byte)
        bytes_remaining -= 1
        if bytes_remaining == 0:
            state = "VERIFY_CHECKSUM"
    
    elif state == "VERIFY_CHECKSUM":
        received_checksum = byte
        calculated = calculate_checksum(packet_buffer[1:])  # Skip header
        
        if received_checksum == calculated:
            process_packet(packet_buffer)
        
        state = "WAIT_HEADER"  # Ready for next packet
```

---

## 🔌 Code Implementation

### Sending (in rosmaster_driver.py)

```python
def set_car_motion(self, v_x, v_y, v_z):
    # Convert to mm/s
    vx_mm = int(v_x * 1000)
    vy_mm = int(v_y * 1000)
    vz_mm = int(v_z * 1000)
    
    # Pack into bytes (little-endian)
    vx_bytes = struct.pack('h', vx_mm)  # 'h' = signed short (2 bytes)
    vy_bytes = struct.pack('h', vy_mm)
    vz_bytes = struct.pack('h', vz_mm)
    
    # Build packet
    cmd = [
        0xFF,              # Header
        0xFC,              # Device ID
        0x0B,              # Length
        0x12,              # Function (MOTION)
        0x07,              # Car type (OrbiBot)
        vx_bytes[0], vx_bytes[1],  # vx low, high
        vy_bytes[0], vy_bytes[1],  # vy low, high
        vz_bytes[0], vz_bytes[1],  # vz low, high
    ]
    
    # Calculate checksum
    checksum = sum(cmd[1:], 257 - 0xFC) & 0xFF  # Skip header, add complement
    cmd.append(checksum)
    
    # Send
    with self._write_lock:
        self.ser.write(cmd)
```

### Receiving (in rosmaster_driver.py)

```python
def _receive_data(self):
    self.ser.reset_input_buffer()
    
    while self._running:
        try:
            # Read one byte
            data = self.ser.read(1)
            if not data:
                continue
            
            byte = data[0]
            
            # State machine parsing...
            # (simplified for clarity)
            
            if byte == 0xFF:  # Header found
                # Read rest of packet...
                device_id = self.ser.read(1)[0]
                length = self.ser.read(1)[0]
                func = self.ser.read(1)[0]
                data_bytes = self.ser.read(length - 2)
                checksum = self.ser.read(1)[0]
                
                # Verify checksum
                calc_checksum = (device_id + length + func + sum(data_bytes) + (257-0xFC)) & 0xFF
                
                if calc_checksum == checksum:
                    self._parse_data(func, data_bytes)
                    
        except serial.SerialException:
            # Handle disconnect...
            pass
```

---

## 🧪 Hands-On: Inspecting Serial Data

### Using `screen` (Direct Serial Monitor)

```bash
# Connect to serial port
screen /dev/motordriver 115200

# You'll see binary garbage (normal!)
# Press Ctrl+A then K to quit
```

### Using Python (Simple Sniffer)

```python
import serial

# Open port
ser = serial.Serial('/dev/motordriver', 115200)

print("Sniffing serial data...")
while True:
    data = ser.read(1)
    if data:
        byte = data[0]
        # Print hex value
        print(f"0x{byte:02X}", end=" ")
        
        # Newline after each packet (header detected)
        if byte == 0xFF:
            print("\n--- New packet ---")
```

---

## 📊 Data Types in Packets

### Integer Encoding

| Type | Bytes | Range | Usage |
|------|-------|-------|-------|
| `uint8` | 1 | 0 to 255 | Battery voltage, small values |
| `int16` | 2 | -32768 to 32767 | Velocities, PID gains |
| `int32` | 4 | -2B to +2B | Encoder counts, positions |

### Endianness

**Little-endian** = Least significant byte first

```
Value: 500 = 0x01F4

Big-endian:    [0x01, 0xF4]
Little-endian: [0xF4, 0x01]  ← OrbiBot uses this!
```

---

## 🎯 Key Takeaways

1. **Serial = One bit at a time** - Simple but effective
2. **Binary protocols are compact** - Essential for real-time control
3. **Packets have structure** - Header, length, function, data, checksum
4. **Checksums detect errors** - Critical for reliability
5. **Little-endian encoding** - Important for data interpretation

---

## 📚 Next Steps

Now you understand serial communication. Next, see the hardware node implementation:

**→ Continue to:** [04 - Hardware Node Deep Dive](04-hardware-node-deep-dive.md)

---

## 💭 Review Questions

1. **Why use binary instead of text protocols for robots?**
   <details>
   <summary>Click for answer</summary>
   Binary is more compact, faster to parse, and uses less CPU - critical for real-time control.
   </details>

2. **What does the checksum protect against?**
   <details>
   <summary>Click for answer</summary>
   Corrupted data during transmission. If a bit flips, the checksum won't match and the packet is rejected.
   </details>

3. **Why little-endian encoding?**
   <details>
   <summary>Click for answer</summary>
   Most microcontrollers (including STM32) use little-endian natively. Makes firmware implementation simpler.
   </details>

---

**You now understand how robots talk! 🔌**