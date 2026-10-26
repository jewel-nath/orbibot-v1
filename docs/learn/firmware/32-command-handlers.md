# Part 3: Command Handlers

**Duration**: 30 minutes  
**Prerequisites**: [Part 3: Packet Structure](31-packet-structure.md)

---

## Learning Objectives

After this lesson, you will understand:
- How the firmware processes incoming commands
- The command dispatch system
- How each command is implemented
- Critical sections for shared data
- Error handling in commands

---

## Command Processing Flow

```
┌─────────────────────────────────────────────────────────┐
│              Command Processing Pipeline                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. RECEIVE                                              │
│     UART ISR → Byte received → Protocol state machine   │
│     ↓                                                    │
│  2. PARSE                                                │
│     State machine assembles packet → Validate checksum  │
│     ↓                                                    │
│  3. DISPATCH                                             │
│     Extract function code → Switch to handler           │
│     ↓                                                    │
│  4. EXECUTE                                              │
│     Handler extracts data → Updates shared variables    │
│     ↓                                                    │
│  5. RESPONSE (optional)                                  │
│     Send acknowledgment or data back to Pi              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## State Machine Parser

### Parser States

```c
// protocol.c - State machine for packet parsing

typedef enum {
    RX_STATE_WAIT_HEADER,    // Waiting for 0xFF
    RX_STATE_WAIT_DEVICE,    // Waiting for device ID
    RX_STATE_WAIT_LENGTH,    // Waiting for length byte
    RX_STATE_READ_DATA       // Reading payload
} rx_state_t;

// Global state
static rx_state_t rx_state = RX_STATE_WAIT_HEADER;
static uint8_t rx_buffer[256];
static uint8_t rx_index = 0;
static uint8_t packet_length = 0;
```

### Byte Reception (ISR)

```c
// Called from UART interrupt when byte received
void protocol_receive_byte(uint8_t byte)
{
    switch (rx_state) {
        case RX_STATE_WAIT_HEADER:
            if (byte == 0xFF) {
                rx_buffer[0] = byte;
                rx_index = 1;
                rx_state = RX_STATE_WAIT_DEVICE;
            }
            // else: ignore, stay in this state
            break;
            
        case RX_STATE_WAIT_DEVICE:
            if (byte == 0xFC) {  // Valid device ID (Pi to STM32)
                rx_buffer[1] = byte;
                rx_index = 2;
                rx_state = RX_STATE_WAIT_LENGTH;
            } else {
                // Invalid device ID, reset
                rx_state = RX_STATE_WAIT_HEADER;
            }
            break;
            
        case RX_STATE_WAIT_LENGTH:
            packet_length = byte + 2;  // Total packet length
            if (packet_length > 4 && packet_length <= 256) {
                rx_buffer[2] = byte;
                rx_index = 3;
                rx_state = RX_STATE_READ_DATA;
            } else {
                // Invalid length, reset
                rx_state = RX_STATE_WAIT_HEADER;
            }
            break;
            
        case RX_STATE_READ_DATA:
            rx_buffer[rx_index++] = byte;
            
            // Check if packet complete
            if (rx_index >= packet_length) {
                // Validate checksum
                if (validate_checksum(rx_buffer, packet_length)) {
                    // Set flag for task to process
                    packet_ready = 1;
                }
                // Reset for next packet
                rx_state = RX_STATE_WAIT_HEADER;
                rx_index = 0;
            }
            break;
    }
}
```

---

## Command Dispatcher

### Main Dispatch Function

```c
// protocol.c - Process received command

void protocol_parse_command(void)
{
    if (!packet_ready) {
        return;  // No packet to process
    }
    
    uint8_t *packet = rx_buffer;
    uint8_t function = packet[3];  // Function code at byte 3
    
    // Dispatch to handler
    switch (function) {
        case FUNC_MOTION:
            handle_motion(&packet[4]);  // Data starts at byte 4
            break;
            
        case FUNC_AUTO_REPORT:
            handle_auto_report(&packet[4]);
            break;
            
        case FUNC_BEEP:
            handle_beep(&packet[4]);
            break;
            
        case FUNC_RESET_ODOM:
            handle_reset_odom();
            break;
            
        case FUNC_SET_MOTOR_PID:
            handle_set_motor_pid(&packet[4]);
            break;
            
        case FUNC_SET_YAW_PID:
            handle_set_yaw_pid(&packet[4]);
            break;
            
        case FUNC_VERSION:
            handle_version();
            break;
            
        default:
            // Unknown command - ignore or send error
            DEBUG_ERROR("Unknown function: 0x%02X\n", function);
            break;
    }
    
    packet_ready = 0;  // Clear flag
}
```

---

## Command Handlers

### 1. MOTION Command Handler (0x12)

```c
// Handle velocity command from ROS

void handle_motion(const uint8_t *data)
{
    // Extract velocities (little-endian int16)
    // data[0] = car type (ignored for now)
    
    int16_t vx_raw = (data[2] << 8) | data[1];  // Vx mm/s
    int16_t vy_raw = (data[4] << 8) | data[3];  // Vy mm/s
    int16_t vz_raw = (data[6] << 8) | data[5];  // Vz mrad/s
    
    // Convert to m/s and rad/s
    float vx = vx_raw / 1000.0f;
    float vy = vy_raw / 1000.0f;
    float omega = vz_raw / 1000.0f;
    
    // Clamp to safe limits
    if (vx > MAX_LINEAR_VELOCITY) vx = MAX_LINEAR_VELOCITY;
    if (vx < -MAX_LINEAR_VELOCITY) vx = -MAX_LINEAR_VELOCITY;
    if (vy > MAX_LINEAR_VELOCITY) vy = MAX_LINEAR_VELOCITY;
    if (vy < -MAX_LINEAR_VELOCITY) vy = -MAX_LINEAR_VELOCITY;
    if (omega > MAX_ANGULAR_VELOCITY) omega = MAX_ANGULAR_VELOCITY;
    if (omega < -MAX_ANGULAR_VELOCITY) omega = -MAX_ANGULAR_VELOCITY;
    
    // Update target velocity (shared with control task)
    // CRITICAL SECTION: Protect shared variable
    taskENTER_CRITICAL();
    target_velocity.vx = vx;
    target_velocity.vy = vy;
    target_velocity.omega = omega;
    taskEXIT_CRITICAL();
    
    // Update command timestamp (for timeout safety)
    last_command_time = xTaskGetTickCount();
    
    DEBUG_VERBOSE("Motion: vx=%.2f, vy=%.2f, w=%.2f\n", vx, vy, omega);
}
```

**Why Critical Section?**
```
Control Task (Priority 10) reads target_velocity
Comm Task (Priority 9) writes target_velocity

Without protection:
  1. Comm task starts writing (vx updated, vy not yet)
  2. Control task preempts, reads partially updated data
  3. Result: Corrupted velocity command!

With critical section:
  1. Comm task enters critical section (interrupts disabled)
  2. Comm task completes write
  3. Comm task exits critical section
  4. Control task reads complete, consistent data
```

---

### 2. AUTO_REPORT Handler (0x01)

```c
// Enable/disable automatic data streaming

void handle_auto_report(const uint8_t *data)
{
    uint8_t enable = data[0];
    
    if (enable == 0x00) {
        auto_report_enabled = 0;
        DEBUG_INFO("Auto-report disabled\n");
    } else if (enable == 0x01) {
        auto_report_enabled = 1;
        report_counter = 0;  // Reset cycle
        DEBUG_INFO("Auto-report enabled\n");
    } else {
        DEBUG_ERROR("Invalid auto-report value: %d\n", enable);
    }
}
```

---

### 3. BEEP Handler (0x02)

```c
// Control buzzer

void handle_beep(const uint8_t *data)
{
    uint16_t duration = (data[1] << 8) | data[0];
    
    if (duration == 0) {
        // Turn off
        BUZZER_OFF();
        buzzer_on_time = 0;
    } else if (duration == 1) {
        // Continuous on
        BUZZER_ON();
        buzzer_on_time = 1;
    } else {
        // Timed beep
        BUZZER_ON();
        buzzer_on_time = duration;  // ms
        buzzer_start_tick = xTaskGetTickCount();
    }
    
    DEBUG_VERBOSE("Beep: %d ms\n", duration);
}

// Called from monitoring task to check buzzer timeout
void protocol_update_buzzer(void)
{
    if (buzzer_on_time >= 10) {  // Timed mode
        uint32_t elapsed = (xTaskGetTickCount() - buzzer_start_tick) 
                          * portTICK_PERIOD_MS;
        if (elapsed >= buzzer_on_time) {
            BUZZER_OFF();
            buzzer_on_time = 0;
        }
    }
}
```

---

### 4. RESET_ODOM Handler (0x09)

```c
// Reset odometry to zero

void handle_reset_odom(void)
{
    // Call control task function
    control_reset_odometry();
    
    DEBUG_INFO("Odometry reset\n");
}

// In task_control.c
void control_reset_odometry(void)
{
    taskENTER_CRITICAL();
    odom.x = 0.0f;
    odom.y = 0.0f;
    odom.theta = 0.0f;
    taskEXIT_CRITICAL();
}
```

---

### 5. SET_MOTOR_PID Handler (0x13)

```c
// Update motor PID gains

void handle_set_motor_pid(const uint8_t *data)
{
    // Extract gains (scaled by 1000)
    int16_t kp_raw = (data[1] << 8) | data[0];
    int16_t ki_raw = (data[3] << 8) | data[2];
    int16_t kd_raw = (data[5] << 8) | data[4];
    uint8_t save_flag = data[6];
    
    // Convert to float
    float kp = kp_raw / 1000.0f;
    float ki = ki_raw / 1000.0f;
    float kd = kd_raw / 1000.0f;
    
    // Validate ranges
    if (kp < 0.0f || kp > 10.0f) {
        DEBUG_ERROR("Invalid Kp: %.3f\n", kp);
        return;
    }
    if (ki < 0.0f || ki > 10.0f) {
        DEBUG_ERROR("Invalid Ki: %.3f\n", ki);
        return;
    }
    if (kd < 0.0f || kd > 10.0f) {
        DEBUG_ERROR("Invalid Kd: %.3f\n", kd);
        return;
    }
    
    // Update PID (thread-safe function)
    control_set_motor_pid(kp, ki, kd);
    
    // Save to flash if requested
    if (save_flag == SAVE_VERIFY) {
        flash_storage_save();
        DEBUG_INFO("PID saved to flash\n");
    }
    
    DEBUG_INFO("PID updated: Kp=%.3f, Ki=%.3f, Kd=%.3f\n", kp, ki, kd);
}
```

---

## Response Sending

### Send Speed Report (0x0A)

```c
void protocol_send_speed_report(void)
{
    uint8_t packet[12];
    int16_t vx, vy, vz;
    uint8_t battery;
    
    // Get measured velocity (from control task)
    control_get_measured_velocity(&vx, &vy, &vz);
    
    // Get battery voltage
    battery = (uint8_t)(battery_get_voltage() * 10.0f);
    
    // Build packet
    packet[0] = 0xFF;           // Header
    packet[1] = 0xFB;           // Device ID (STM32 to Pi)
    packet[2] = 0x08;           // Length
    packet[3] = FUNC_REPORT_SPEED;  // Function
    
    // Data (little-endian)
    packet[4] = vx & 0xFF;
    packet[5] = (vx >> 8) & 0xFF;
    packet[6] = vy & 0xFF;
    packet[7] = (vy >> 8) & 0xFF;
    packet[8] = vz & 0xFF;
    packet[9] = (vz >> 8) & 0xFF;
    packet[10] = battery;
    
    // Checksum
    packet[11] = calculate_checksum(packet, 12);
    
    // Send via UART
    hal_usart_send_bytes(packet, 12);
}
```

---

## Error Handling

### Checksum Validation

```c
uint8_t validate_checksum(const uint8_t *packet, uint8_t length)
{
    uint16_t sum = 0;
    
    // Sum bytes [1] to [length-2] (exclude header and checksum)
    for (uint8_t i = 1; i < length - 1; i++) {
        sum += packet[i];
    }
    
    uint8_t calculated = sum & 0xFF;
    uint8_t received = packet[length - 1];
    
    return (calculated == received) ? 1 : 0;
}
```

### Invalid Packet Handling

```c
void protocol_handle_error(error_type_t error)
{
    switch (error) {
        case ERROR_CHECKSUM:
            DEBUG_ERROR("Checksum failed\n");
            checksum_error_count++;
            break;
            
        case ERROR_LENGTH:
            DEBUG_ERROR("Invalid packet length\n");
            break;
            
        case ERROR_DEVICE_ID:
            DEBUG_ERROR("Invalid device ID\n");
            break;
            
        case ERROR_TIMEOUT:
            DEBUG_ERROR("Packet timeout\n");
            rx_state = RX_STATE_WAIT_HEADER;  // Reset
            break;
    }
}
```

---

## Thread Safety Summary

### Shared Data Protection

| Shared Variable | Accessed By | Protection |
|-----------------|-------------|------------|
| `target_velocity` | Comm (write), Control (read) | Critical section |
| `current_odometry` | Control (write), Comm (read) | Critical section |
| `imu_attitude` | IMU (write), Comm (read) | Critical section |
| `battery_voltage` | Monitor (write), Comm (read) | Critical section |
| `pid_gains` | Comm (write), Control (read) | Critical section |

### Why Not Mutex?

For simple data copies, critical sections are:
- **Faster**: No OS overhead
- **Simpler**: Just disable interrupts briefly
- **Safer**: No risk of priority inversion

Use mutex for longer critical sections or when sleeping.

---

## Exercise: Parse a Command

**Given**: Received MOTION packet data bytes:
```
[0x00][0x2C][0x01][0x00][0x00][0x00][0x00]
```

**Task**: Write code to extract velocities

**Answer**:

<details>
<summary>Click for answer</summary>

```c
void parse_motion_data(const uint8_t *data)
{
    // data[0] = car type (ignore)
    
    // Extract int16 velocities (little-endian)
    int16_t vx_raw = (data[2] << 8) | data[1];
    int16_t vy_raw = (data[4] << 8) | data[3];
    int16_t vz_raw = (data[6] << 8) | data[5];
    
    // Convert to float (m/s and rad/s)
    float vx = vx_raw / 1000.0f;
    float vy = vy_raw / 1000.0f;
    float omega = vz_raw / 1000.0f;
    
    printf("Vx: %.2f m/s, Vy: %.2f m/s, Omega: %.3f rad/s\n",
           vx, vy, omega);
}

// Result: Vx = 0.30 m/s, Vy = 0.00 m/s, Omega = 0.00 rad/s
```

</details>

---

## Summary

- **State machine**: Parses incoming bytes into packets
- **Dispatcher**: Routes commands to appropriate handler
- **Handlers**: Extract data, validate, update shared variables
- **Critical sections**: Protect shared data access
- **Responses**: Send data back to Pi when needed
- **Error handling**: Checksum validation, range checks

---

## Next Lesson

[Part 3: Auto-Reporting](33-auto-reporting.md) - Automatic data streaming

---

*OrbiBot Firmware Study Guide*  
*Part 3 of 10*