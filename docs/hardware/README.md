# Hardware

What is on OrbiBot V1. The first part was **measured on the robot** on
2026-08-02, not copied from datasheets; the parts list after it gives the
datasheet values. For the motor board's pins, timers and power rails, see
[the ROSMaster board reference](rosmaster-board.md).

## On the robot (measured 2026-08-02)

### Computer: Raspberry Pi 5 Model B

| | |
|---|---|
| CPU | 4 × Cortex-A76 at 2.4 GHz (aarch64) |
| RAM | 7.8 GiB; 1.7 used and 6.1 available at idle |
| OS | Ubuntu 24.04.4 LTS, ROS 2 Jazzy |
| Storage | 58 GB card, 43 GB free |
| Temperature | 49.4 °C at idle, no throttling (`throttled=0x0`) |

### Motor board: Yahboom ROSMaster V3.0

An STM32F103RCT6 (Cortex-M3 at 72 MHz, no FPU) running OrbiBot's own
firmware on FreeRTOS, with 4 tasks.

| Resource | Used | Free |
|---|---|---|
| Flash, 256 KB | 28.4 KB (10.9 %) | about 228 KB |
| RAM, 48 KB | 19.9 KB (40.4 %) | about 29 KB |

Measured with GCC 12.3 on the Pi. Memory is not the limit for new firmware
features; CPU time is. See
[the firmware architecture](../../src/orbibot_rosmaster_firmware/firmware-architecture.md).

| On the board | Used? | Notes |
|---|---|---|
| 4 × AM2857 H-bridges | Used | 20 kHz PWM, period 3600, dead zone 1600 |
| 4 × JGB37-520 motors | Used | 30:1 gearbox, 333 RPM with no load at 12 V |
| 4 × quadrature encoders | Used | 1320 counts per wheel turn; directions checked 2026-08-02 |
| ICM-20948 IMU (SPI2) | Used: gyro and accelerometer | ±500 dps, ±2 g. Its AK09916 magnetometer is not used since 2026-04-28 |
| Battery ADC | Used | 4S LiFePO4, divider 4.03, read once a second |
| Buzzer (PC5) | Used | |
| SSD1306 OLED | Partly used | The firmware draws on it (its driver is set up for 128 × 32); no serial command drives it |
| User button (PD2) | Not used | A free input: a physical stop button would need no new parts |
| CAN (SN65HVD230) | Not used | Its pins clash with USB and the motors |
| 4 × servo outputs, 6.8 V | Not used | |
| RGB LED (WS2812) | Removed | Dropped from the firmware on purpose |

### Body

The mass and the frame size are the robot model's values
(`orbibot.urdf.xacro`), not weighed or measured.

| | |
|---|---|
| Frame | Welded stainless steel |
| Mass | About 6 kg |
| Frame size | 350 × 250 mm (the wheels stick out beyond it) |
| Wheelbase × track | 260 × 360 mm (front to back × left to right, wheel centres) |
| Wheels | 100 mm steel mecanum, ABBA layout |

### USB devices

| Device | Bus | Link speed | Topic |
|---|---|---|---|
| RPLIDAR A1 | CP2102 USB serial, `/dev/lidar` | 12 Mbps | `/scan` |
| ROSMaster board | CH340 USB serial, `/dev/motordriver` | 12 Mbps | (115200 baud) |
| RealSense D435 | USB | **480 Mbps** | `/camera/*`, 15 Hz configured |

**The RealSense ran on a USB 2 link.** At 480 Mbps the D435 can't deliver
depth and colour at a useful resolution together, and the driver drops or
refuses stream combinations. On V1 the camera launch is off by default, and
the web dashboard uses its colour stream. Moving it to a USB 3 port with a
USB 3 cable should fix the link. To check a camera's link speed:

```bash
for d in /sys/bus/usb/devices/*/; do
  [ -f "$d/product" ] && echo "$(cat $d/product) — $(cat $d/speed) Mbps"
done | grep -i realsense
```

The udev rules from `src/orbibot_hardware/scripts/setup_permissions.sh` give
the LiDAR and the motor board their fixed names, `/dev/lidar` and
`/dev/motordriver`.

### Not installed

| Package | Why it matters |
|---|---|
| `ros-jazzy-twist-mux` | Nothing chooses between the four `/cmd_vel` publishers; see [the command pipeline](../architecture/command-pipeline.md) |
| `ros-jazzy-joy` | Needed only by the switched-off gamepad package, `orbibot_teleop` |

## Parts list (datasheet values)

| Part | Key figures |
|---|---|
| Raspberry Pi 5, 8 GB | 4 × Cortex-A76 at 2.4 GHz; 2 × USB 3, 2 × USB 2; 5 V at up to 5 A |
| Yahboom ROS Robot Control Board V3.0 | STM32F103RCT6; 12 V in (9–16 V); 5.1 V / 5 A out to the Pi over USB-C; 4 motor channels with encoders |
| 4 × JGB37-520 geared motors | 12 V; 333 ± 10 RPM; 1:30; 3.3 kg·cm rated, 4.8 kg·cm stall; Hall encoder, 11 pulses per motor turn |
| 4 × 100 mm steel mecanum wheels | 50 mm wide, 45° rollers, 400 g each |
| RPLIDAR A1 | 360°, 0.15–12 m; 5.5 Hz nominal, up to 10 Hz; up to 1,450 points per turn; 115200 baud |
| Intel RealSense D435 | Active IR stereo; depth up to 1280 × 720; 87° × 58° depth field of view |
| Battery | 4S LiFePO4, 12.8 V nominal, 14.6 V full; IFR-32140 cells, 15.5 Ah; about 198 Wh |
| BMS | 4S 100 A LiFePO4 BMS with balancing; cuts off at 15 V and 10 V |

**Speed, worked out from the datasheets, not measured:** a 100 mm wheel goes
314 mm per turn, so 333 RPM would be about 1.74 m/s. The firmware limits the
robot to 1.0 m/s, and Nav2 to 0.5 m/s.

The firmware's own battery thresholds are 11.0 V for the warning and 10.5 V
for the cut-off (`include/orbibot_config.h`).
