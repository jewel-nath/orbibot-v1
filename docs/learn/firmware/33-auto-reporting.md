---
title: "Part 3: Auto-Reporting"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "20 minutes"
tags:
  - learn
  - firmware
---

# Part 3: Auto-Reporting

**Duration**: 20 minutes  
**Prerequisites**: [[32-command-handlers]]

---

## Learning Objectives

After this lesson, you will understand:
- How auto-reporting works
- The 50ms reporting cycle
- What data is sent and when
- How to enable/disable streaming
- Bandwidth considerations

---

## What is Auto-Reporting?

Auto-reporting automatically sends sensor data from STM32 to Raspberry Pi without the Pi asking for it.

```
Without Auto-Report (Polling):
  Pi: "Send encoder data" → STM32: "Here are encoders"
  Pi: "Send IMU data" → STM32: "Here is IMU"
  Pi: "Send battery" → STM32: "Here is battery"
  (Lots of back-and-forth, inefficient)

With Auto-Report (Streaming):
  STM32: "Here's speed + battery"
  STM32: "Here's IMU raw"
  STM32: "Here's attitude"
  STM32: "Here's encoders"
  (Continuous stream, efficient)
```

---

## Reporting Cycle

### 50ms Cycle (20Hz Effective)

Data is sent in a repeating 50ms cycle:

```
Time (ms) →
0     10    20    30    40    50    60    70    80    90   100
├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│Speed│     │Raw  │     │Enc  │     │Speed│     │Raw  │     │
│+Bat │     │IMU  │     │     │     │+Bat │     │IMU  │     │
├─────┴─────┼─────┴─────┼─────┴─────┼─────┴─────┼─────┴─────┤
            │ Attitude  │           │ Attitude  │
            └───────────┘           └───────────┘
            
Every 50ms:
  0ms:   REPORT_SPEED (velocity + battery)
  20ms:  REPORT_ICM_RAW (raw IMU data)
  25ms:  REPORT_IMU_ATT (attitude angles) - inside 20-30ms window
  40ms:  REPORT_ENCODER (wheel counts)
  50ms:  Cycle repeats
```

### Data Rates

| Report Type | Interval | Rate | Size |
|-------------|----------|------|------|
| Speed + Battery | 50ms | 20 Hz | 7 bytes |
| IMU Raw | 50ms | 20 Hz | 18 bytes |
| IMU Attitude | 50ms | 20 Hz | 6 bytes |
| Encoders | 50ms | 20 Hz | 16 bytes |
| **Total** | **-** | **-** | **~940 bytes/sec** |

At 115200 baud (14400 bytes/sec), this uses only ~6% of bandwidth.

---

## Implementation

### Communication Task with Auto-Report

```c
// From: task_communication.c

// Auto-report state
volatile uint8_t auto_report_enabled = 0;
static uint16_t report_counter = 0;

void task_communication(void *params)
{
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(1);  // 1ms check rate
    
    for (;;)
    {
        // 1. Check for incoming commands (always)
        if (protocol_packet_ready()) {
            protocol_parse_command();
        }
        
        // 2. Send auto-reports (if enabled)
        if (auto_report_enabled)
        {
            switch (report_counter) {
                case 0:    // 0ms - Speed + Battery
                    protocol_send_speed_report();
                    break;
                    
                case 20:   // 20ms - Raw IMU
                    protocol_send_imu_raw_report();
                    break;
                    
                case 25:   // 25ms - Attitude (after raw)
                    protocol_send_imu_attitude_report();
                    break;
                    
                case 40:   // 40ms - Encoders
                    protocol_send_encoder_report();
                    break;
                    
                case 50:   // 50ms - Reset cycle
                    report_counter = 0;
                    break;
            }
            
            report_counter++;
        }
        
        vTaskDelayUntil(&last_wake, period);
    }
}
```

---

## Report Functions

### 1. Speed Report (0x0A)

Sends measured velocity and battery voltage.

```c
void protocol_send_speed_report(void)
{
    uint8_t packet[12];
    int16_t vx, vy, vz;
    
    // Get measured velocity from control task
    control_get_measured_velocity(&vx, &vy, &vz);
    
    // Get battery voltage
    uint8_t battery = (uint8_t)(battery_get_voltage() * 10.0f);
    
    // Build packet
    packet[0] = 0xFF;                    // Header
    packet[1] = 0xFB;                    // Device ID
    packet[2] = 0x08;                    // Length
    packet[3] = FUNC_REPORT_SPEED;       // Function 0x0A
    packet[4] = vx & 0xFF;               // Vx low
    packet[5] = (vx >> 8) & 0xFF;        // Vx high
    packet[6] = vy & 0xFF;               // Vy low
    packet[7] = (vy >> 8) & 0xFF;        // Vy high
    packet[8] = vz & 0xFF;               // Vz low
    packet[9] = (vz >> 8) & 0xFF;        // Vz high
    packet[10] = battery;                // Battery (×10)
    packet[11] = calculate_checksum(packet, 12);
    
    // Send
    hal_usart_send_bytes(packet, 12);
}
```

### 2. IMU Raw Report (0x0E)

Sends raw accelerometer, gyroscope, and magnetometer data.

```c
void protocol_send_imu_raw_report(void)
{
    uint8_t packet[22];
    int16_t gyro[3], accel[3], mag[3];
    
    // Get raw IMU data
    imu_get_all_raw(gyro, accel, mag);
    
    // Build packet (each value is int16, little-endian)
    packet[0] = 0xFF;
    packet[1] = 0xFB;
    packet[2] = 0x12;                    // Length = 18
    packet[3] = FUNC_REPORT_ICM_RAW;     // Function 0x0E
    
    // Gyroscope (X, Y, Z)
    packet[4] = gyro[0] & 0xFF;
    packet[5] = (gyro[0] >> 8) & 0xFF;
    packet[6] = gyro[1] & 0xFF;
    packet[7] = (gyro[1] >> 8) & 0xFF;
    packet[8] = gyro[2] & 0xFF;
    packet[9] = (gyro[2] >> 8) & 0xFF;
    
    // Accelerometer (X, Y, Z)
    packet[10] = accel[0] & 0xFF;
    packet[11] = (accel[0] >> 8) & 0xFF;
    packet[12] = accel[1] & 0xFF;
    packet[13] = (accel[1] >> 8) & 0xFF;
    packet[14] = accel[2] & 0xFF;
    packet[15] = (accel[2] >> 8) & 0xFF;
    
    // Magnetometer (X, Y, Z)
    packet[16] = mag[0] & 0xFF;
    packet[17] = (mag[0] >> 8) & 0xFF;
    packet[18] = mag[1] & 0xFF;
    packet[19] = (mag[1] >> 8) & 0xFF;
    packet[20] = mag[2] & 0xFF;
    packet[21] = (mag[2] >> 8) & 0xFF;
    
    // Checksum
    packet[22] = calculate_checksum(packet, 23);
    
    hal_usart_send_bytes(packet, 23);
}
```

### 3. IMU Attitude Report (0x0C)

Sends roll, pitch, and yaw angles.

```c
void protocol_send_imu_attitude_report(void)
{
    uint8_t packet[10];
    float roll, pitch, yaw;
    
    // Get attitude from IMU task
    imu_task_get_attitude(&roll, &pitch, &yaw);
    
    // Convert to int16 (radians × 10000)
    int16_t roll_int = (int16_t)(roll * 10000.0f);
    int16_t pitch_int = (int16_t)(pitch * 10000.0f);
    int16_t yaw_int = (int16_t)(yaw * 10000.0f);
    
    // Build packet
    packet[0] = 0xFF;
    packet[1] = 0xFB;
    packet[2] = 0x06;                    // Length
    packet[3] = FUNC_REPORT_IMU_ATT;     // Function 0x0C
    packet[4] = roll_int & 0xFF;
    packet[5] = (roll_int >> 8) & 0xFF;
    packet[6] = pitch_int & 0xFF;
    packet[7] = (pitch_int >> 8) & 0xFF;
    packet[8] = yaw_int & 0xFF;
    packet[9] = (yaw_int >> 8) & 0xFF;
    packet[10] = calculate_checksum(packet, 11);
    
    hal_usart_send_bytes(packet, 11);
}
```

### 4. Encoder Report (0x0D)

Sends wheel encoder counts.

```c
void protocol_send_encoder_report(void)
{
    uint8_t packet[21];
    
    // Get encoder counts
    int32_t enc[4];
    for (int i = 0; i < 4; i++) {
        enc[i] = encoder_get_count(i);
    }
    
    // Build packet
    packet[0] = 0xFF;
    packet[1] = 0xFB;
    packet[2] = 0x11;                    // Length = 17
    packet[3] = FUNC_REPORT_ENCODER;     // Function 0x0D
    
    // Each encoder: 4 bytes, little-endian
    for (int i = 0; i < 4; i++) {
        packet[4 + i*4] = enc[i] & 0xFF;
        packet[5 + i*4] = (enc[i] >> 8) & 0xFF;
        packet[6 + i*4] = (enc[i] >> 16) & 0xFF;
        packet[7 + i*4] = (enc[i] >> 24) & 0xFF;
    }
    
    packet[20] = calculate_checksum(packet, 21);
    
    hal_usart_send_bytes(packet, 21);
}
```

---

## Enabling Auto-Report

### Command to Enable

```c
// From Pi: Enable auto-report
uint8_t enable_packet[] = {
    0xFF,       // Header
    0xFC,       // Device ID (Pi to STM32)
    0x03,       // Length
    0x01,       // Function (AUTO_REPORT)
    0x01,       // Enable = 1
    0x01        // Checksum (0xFC + 0x03 + 0x01 + 0x01 = 0x0101 → 0x01)
};
```

### Handler Implementation

```c
void handle_auto_report(const uint8_t *data)
{
    uint8_t enable = data[0];
    
    if (enable == 0x01) {
        auto_report_enabled = 1;
        report_counter = 0;  // Reset to start of cycle
        DEBUG_INFO("Auto-report enabled\n");
    } else {
        auto_report_enabled = 0;
        DEBUG_INFO("Auto-report disabled\n");
    }
}
```

---

## Data Usage Analysis

### Bandwidth Calculation

```
Reports per second:
- Speed: 20 Hz × 12 bytes = 240 bytes/s
- IMU Raw: 20 Hz × 23 bytes = 460 bytes/s
- IMU Att: 20 Hz × 11 bytes = 220 bytes/s
- Encoders: 20 Hz × 21 bytes = 420 bytes/s

Total: 1340 bytes/s

UART at 115200 baud:
- Theoretical max: 115200 / 10 = 11520 bytes/s (8N1)
- Usable: ~14400 bytes/s (with efficient packing)

Utilization: 1340 / 14400 = 9.3%
```

### Buffer Considerations

```c
// UART TX buffer size (in stm32)
#define UART_TX_BUFFER_SIZE 256

// At 1340 bytes/s with 256 byte buffer:
// Buffer holds ~190ms of data
// Safe margin for processing delays
```

---

## Synchronization

### Why Timing Matters

```c
// Bad: Reports drift relative to control loop
// Control loop: 0, 10, 20, 30, 40, 50ms...
// Reports:      5, 15, 25, 35, 45, 55ms...
// Result: Stale data in reports!

// Good: Reports synchronized to control loop
// Use vTaskDelayUntil for precise timing
```

### Timestamp Option

For precise synchronization, add timestamp to reports:

```c
void protocol_send_speed_report_with_time(void)
{
    uint8_t packet[16];
    uint32_t tick = xTaskGetTickCount();
    
    // ... velocity and battery ...
    
    // Add timestamp (ms since boot)
    packet[12] = tick & 0xFF;
    packet[13] = (tick >> 8) & 0xFF;
    packet[14] = (tick >> 16) & 0xFF;
    packet[15] = (tick >> 24) & 0xFF;
    
    // ...
}
```

---

## Exercise: Parse Auto-Report Data

**Given**: You received this speed report packet:
```
[0xFF][0xFB][0x08][0x0A][0xF4][0x01][0x00][0x00][0x00][0x00][0x7E][Checksum]
```

**Extract**:
1. Vx (mm/s)
2. Vy (mm/s)
3. Vz (mrad/s)
4. Battery voltage

**Answer**:

<details>
<summary>Click for answer</summary>

```c
void parse_speed_report(uint8_t *packet)
{
    // Vx = bytes [4,5] as int16 little-endian
    int16_t vx = (packet[5] << 8) | packet[4];
    // vx = 0x01F4 = 500 mm/s = 0.5 m/s
    
    // Vy = bytes [6,7]
    int16_t vy = (packet[7] << 8) | packet[6];
    // vy = 0x0000 = 0 mm/s
    
    // Vz = bytes [8,9]
    int16_t vz = (packet[9] << 8) | packet[8];
    // vz = 0x0000 = 0 mrad/s
    
    // Battery = byte [10]
    uint8_t battery_raw = packet[10];
    // battery = 0x7E = 126 → 12.6V
    
    printf("Vx: %.2f m/s, Vy: %.2f m/s, Vz: %.3f rad/s, Bat: %.1fV\n",
           vx/1000.0f, vy/1000.0f, vz/1000.0f, battery_raw/10.0f);
}

// Output: Vx: 0.50 m/s, Vy: 0.00 m/s, Vz: 0.000 rad/s, Bat: 12.6V
```

</details>

---

## Summary

- **Auto-report**: Continuous data streaming from STM32 to Pi
- **Cycle**: 50ms repeating cycle with 4 report types
- **Rate**: ~1340 bytes/sec (9% of UART bandwidth)
- **Enable**: Send AUTO_REPORT command with enable=1
- **Synchronization**: Reports align with control task timing

---

## Next Lesson

[[09-tf2-transforms]] - Frames and coordinate conventions

---

*OrbiBot Firmware Study Guide*  
*Part 3 of 10*