# OrbiBot Firmware Test Scripts

Clean, modular test scripts for testing OrbiBot firmware functionality.

## Quick Start

```bash
# Run all tests
python3 run_all_tests.py

# Run specific test
python3 test_encoder.py
python3 test_motor_speed.py
python3 test_imu.py
```

## Test Scripts

| Script | Description |
|--------|-------------|
| `run_all_tests.py` | Comprehensive test suite - runs all tests |
| `test_encoder.py` | Test encoder readings from all 4 motors |
| `test_motor_direction.py` | Test individual motor directions |
| `test_motor_speed.py` | Interactive velocity control (WASD keys) |
| `test_imu.py` | Test IMU raw data and attitude angles |
| `test_battery.py` | Monitor battery voltage |
| `test_data_rate.py` | Measure communication data rate |
| `test_oled.py` | Test OLED display |
| `test_beep.py` | Test buzzer |

## Shared Library

`rosmaster_protocol.py` - Shared protocol definitions and utilities:
- `ROSMasterProtocol` - Serial protocol handler
- `PacketMonitor` - Packet counting and monitoring
- Data classes: `SpeedData`, `IMURawData`, `IMUAttitudeData`, `EncoderData`
- Utility functions for colored terminal output

## Common Options

All scripts support:
- `--port`, `-p` - Serial port (default: `/dev/motordriver`)
- `--help`, `-h` - Show help

## Expected Results

### Encoder Test
- Forward wheel rotation = positive delta
- Backward wheel rotation = negative delta

### Motor Direction Test
- All motors should spin forward (robot moves forward)

### IMU Test
- AccZ ~ 16000 when flat (gravity)
- Roll/Pitch change when tilted
- Yaw changes when rotated

### Battery Test
- Normal: 11.0V - 12.6V (3S LiPo)
- Warning: 10.5V - 11.0V
- Critical: < 10.5V

### Data Rate Test
- Expected: ~100 packets/s total
- ~25 packets/s per type (speed, encoder, IMU raw, IMU attitude)

## Troubleshooting

1. **Permission denied**: Add user to dialout group
   ```bash
   sudo usermod -a -G dialout $USER
   ```

2. **Port not found**: Check udev rules or use actual port
   ```bash
   ls -la /dev/ttyUSB*
   python3 test_encoder.py --port /dev/ttyUSB0
   ```

3. **No data received**: Check firmware is running and BOOT0 is LOW
