# orbibot_sensors

Sensor integration for OrbiBot: RPLidar A1 2D LiDAR and Intel RealSense D435 RGB-D camera. Includes LiDAR-based obstacle detection for safety.

## Overview

This package provides sensor drivers and launch configurations for OrbiBot's perception stack. The RPLidar A1 is the primary navigation sensor, while the RealSense D435 provides visual data for advanced applications (optional, disabled by default on Raspberry Pi due to CPU load).

---

## Sensors

### RPLidar A1 (Primary Navigation Sensor)
- **Type**: 360° 2D laser scanner
- **Range**: 0.15–8.0 meters
- **Rate**: 10 Hz (scans per second)
- **Resolution**: ~0.5° (Express mode) or ~1° (Standard mode)
- **Interface**: USB Serial (/dev/lidar)
- **Topics**: `/scan`

### RealSense D435 (Optional Vision Sensor)
- **Type**: RGB-D camera with stereo depth
- **Resolution**: 424×240 @ 15Hz (RPi-optimized) or 640×480 @ 30Hz
- **Range**: 0.4–4.0 meters (depth)
- **Interface**: USB 3.0 (/dev/camera)
- **Topics**: `/camera/color/image_raw`, `/camera/depth/image_rect_raw`

---

## Quick Start

### Launch LiDAR Only
```bash
ros2 launch orbibot_sensors lidar.launch.py
ros2 launch orbibot_sensors lidar.launch.py scan_mode:=Standard  # Slower but compatible
```

### Launch Camera Only
```bash
ros2 launch orbibot_sensors camera.launch.py
ros2 launch orbibot_sensors camera.launch.py enable_pointcloud:=true  # CPU-intensive
```

### Launch Both Sensors
```bash
ros2 launch orbibot_sensors sensors.launch.py              # Both sensors
ros2 launch orbibot_sensors sensors.launch.py sensors:=lidar      # LiDAR only
ros2 launch orbibot_sensors sensors.launch.py sensors:=camera     # Camera only
ros2 launch orbibot_sensors sensors.launch.py sensors:=both enable_camera_to_scan:=true
```

---

## Launch Files

### `lidar.launch.py` — RPLidar A1

| Argument | Default | Description |
|----------|---------|-------------|
| `serial_port` | `/dev/lidar` | USB serial device path |
| `frame_id` | `lidar_link` | TF frame for scan header |
| `scan_mode` | `Express` | `Express` (~0.5° res) or `Standard` (~1° res) |

**Note**: The LiDAR uses `flip_x_axis: true` in firmware to match OrbiBot's physical mounting. The URDF has `rpy="0 0 0"`.

### `camera.launch.py` — RealSense D435

| Argument | Default | Description |
|----------|---------|-------------|
| `camera_name` | `camera` | Namespace prefix for topics |
| `enable_color` | `true` | Enable RGB stream |
| `enable_depth` | `true` | Enable depth stream |
| `enable_pointcloud` | `false` | Enable PointCloud2 (high CPU on RPi) |
| `color_width` | `424` | RGB frame width |
| `color_height` | `240` | RGB frame height |
| `color_fps` | `15` | RGB frame rate |

**RPi Optimization**: Default settings (424×240@15fps, no pointcloud) are tuned for Raspberry Pi 5. Higher resolutions will impact SLAM performance.

### `sensors.launch.py` — Meta-Launcher

| Argument | Default | Description |
|----------|---------|-------------|
| `sensors` | `both` | Which sensors: `lidar`, `camera`, `both` |
| `log_level` | `info` | Log level for all nodes |
| `enable_camera_to_scan` | `false` | Enable depth → LaserScan conversion |

---

## Topics

### Published by RPLidar A1

| Topic | Type | QoS | Rate | Description |
|-------|------|-----|------|-------------|
| `/scan` | `sensor_msgs/LaserScan` | BEST_EFFORT, depth 5 | 10 Hz | 360° laser scan data |

**Scan Parameters**:
- `angle_min`: -π (-180°)
- `angle_max`: +π (+180°)
- `angle_increment`: ~0.0087 rad (~0.5° in Express mode)
- `range_min`: 0.12 m (sensor minimum)
- `range_max`: 8.0 m (sensor maximum)
- `time_increment`: 0.0001 s (time between measurements)

> **Range Filtering**: Actual usable range is 0.15–8.0m. Filtering is done by `slam_toolbox` (`min_laser_range`, `max_laser_range`), not by the driver.

### Published by RealSense D435

| Topic | Type | Rate | Description |
|-------|------|------|-------------|
| `/camera/color/image_raw` | `sensor_msgs/Image` | 15 Hz | RGB image (BGR8 encoding) |
| `/camera/depth/image_rect_raw` | `sensor_msgs/Image` | 15 Hz | Depth image (16UC1, mm) |
| `/camera/color/camera_info` | `sensor_msgs/CameraInfo` | 15 Hz | RGB camera calibration |
| `/camera/depth/camera_info` | `sensor_msgs/CameraInfo` | 15 Hz | Depth camera calibration |
| `/camera/extrinsics/depth_to_color` | `Extrinsics` | Static | Depth-to-RGB transform |

### Published by obstacle_detector

| Topic | Type | QoS | Rate | Description |
|-------|------|-----|------|-------------|
| `/orbibot/obstacle_detected` | `std_msgs/Bool` | RELIABLE, depth 1 | 10 Hz | True if obstacle within warning distance |
| `/orbibot/emergency_stop` | `std_msgs/Bool` | RELIABLE, depth 1 | 10 Hz | True if obstacle within emergency distance |
| `/orbibot/min_obstacle_distance` | `std_msgs/Float32` | RELIABLE, depth 1 | 10 Hz | Closest obstacle distance (meters) |
| `/orbibot/obstacle_sectors` | `std_msgs/Float32MultiArray` | RELIABLE, depth 1 | 10 Hz | 8-sector distances [front→CCW] |

### Subscribed by obstacle_detector

| Topic | Type | QoS | Description |
|-------|------|-----|-------------|
| `/scan` | `sensor_msgs/LaserScan` | BEST_EFFORT, depth 1 | Input LiDAR scan (latest-only) |

---

## obstacle_detector Node

8-sector 360° LiDAR obstacle detection with hysteresis for safety applications.

### Sector Layout
```
              Front (0)
                ↑
    FL (1) ↖       ↗ FR (7)
             ╲     ╱
    Left (2)  ╲   ╱  Right (6)
               ╲ ╱
    BL (3) ↙       ↘ BR (5)
                ↓
              Back (4)
```

### Default Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| `warning_distance` | 0.50 m | Publish `obstacle_detected = true` |
| `emergency_distance` | 0.25 m | Publish `emergency_stop = true` |
| `hysteresis` | 0.05 m | Prevents rapid toggling at threshold |

### Launch with Custom Thresholds
```bash
ros2 run orbibot_sensors obstacle_detector \
  --ros-args \
  -p warning_distance:=0.6 \
  -p emergency_distance:=0.3
```

---

## depthimage_to_laserscan (Optional)

When `enable_camera_to_scan:=true`, the RealSense depth image is converted to a laser scan for detecting low obstacles missed by the LiDAR.

| Parameter | Value | Description |
|-----------|-------|-------------|
| `output_frame` | `camera_depth_frame` | Scan frame_id |
| `range_min` | 0.4 m | Minimum depth distance |
| `range_max` | 4.0 m | Maximum depth distance |
| `scan_height` | 100 | Number of pixel rows to sample |
| `scan_time` | 0.033 s | ~30 Hz effective rate |

**Output Topic**: `/scan_from_camera` (use alongside `/scan` in Nav2)

---

## Configuration Files

| File | Description |
|------|-------------|
| `config/rplidar_params.yaml` | Valid rplidar_composition parameters (9 params only) |
| `config/realsense_camera_params.yaml` | RealSense resolution, filters, frame IDs |

**Note**: `rplidar_params.yaml` contains only valid parameters. Invalid parameters are silently ignored by the driver but create false expectations. See [sensors-changelog.md](sensors-changelog.md) for details.

---

## Device Setup

### udev Rules (Required)

Create `/etc/udev/rules.d/99-orbibot.rules`:

```bash
# RPLidar A1
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="lidar", MODE="0666", GROUP="dialout"

# RealSense D435
SUBSYSTEM=="usb", ATTR{idVendor}=="8086", ATTR{idProduct}=="0b07", SYMLINK+="camera", MODE="0666", GROUP="dialout"

# Motor driver (CH340)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="motordriver", MODE="0666", GROUP="dialout"
```

Reload rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Verify Devices
```bash
ls -la /dev/lidar /dev/camera /dev/motordriver
# Should show symlinks to ttyUSB* or similar
```

---

## Debugging

### Verify LiDAR Publishing
```bash
# Check scan rate
ros2 topic hz /scan
# Expected: ~10Hz

# Inspect scan data
ros2 topic echo /scan --once | head -20
# Check: angle_min, angle_max, range_min, range_max, header.frame_id

# Visualize in RViz
ros2 launch orbibot_description rviz.launch.py
# Add LaserScan display, set topic to /scan
```

### Verify Camera Publishing
```bash
# Check image rates
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_rect_raw
# Expected: ~15Hz each

# View camera feed
ros2 run rqt_image_view rqt_image_view
# Select /camera/color/image_raw
```

### Check obstacle_detector
```bash
# Monitor safety signals
ros2 topic echo /orbibot/obstacle_detected
ros2 topic echo /orbibot/min_obstacle_distance

# Simulate obstacle (place object in front of robot)
# Should see obstacle_detected toggle to true
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `/dev/lidar` not found | udev rules not applied | Check `sudo dmesg \| grep ttyUSB`, reload udev rules |
| No scan data | LiDAR not spinning | Check USB power, motor PWM setting |
| Camera not detected | USB 2.0 port or insufficient power | Use USB 3.0 port, powered hub |
| High CPU usage | Camera resolution too high | Use 424×240@15fps (default), disable pointcloud |
| Obstacle detector false positives | Thresholds too sensitive | Increase `warning_distance` to 0.7m |

---

## Dependencies

```bash
# RPLidar driver
sudo apt install ros-jazzy-rplidar-ros

# RealSense driver
sudo apt install ros-jazzy-realsense2-camera

# Depth image to laser scan (optional)
sudo apt install ros-jazzy-depthimage-to-laserscan
```

---

## References

- **RPLidar A1 Datasheet**: https://www.slamtec.com/en/Lidar/A1Spec
- **RealSense D435**: https://www.intelrealsense.com/depth-camera-d435/
- **rplidar_ros**: https://github.com/Slamtec/rplidar_ros
- **realsense-ros**: https://github.com/IntelRealSense/realsense-ros

---

**Last Updated**: 2026-02-24  
**Maintainer**: Jewel Nath