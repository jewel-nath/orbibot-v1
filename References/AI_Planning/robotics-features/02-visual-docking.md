# 2. Visual Docking / Precision Parking

**Difficulty:** Moderate
**Hardware Used:** RealSense D435
**Prerequisites:** None (foundational feature)

## Description

Use visual markers (AprilTags/ArUco) or shape detection to dock precisely, specifically useful for charging.

## Implementation

- Mecanum wheels allow for precise X and Y adjustments (strafing) to align perfectly with a connector
- The standard Lidar navigation gets you close (e.g., within 0.5m), and the Vision system takes over for the final approach
- Visual servoing loop adjusts position based on marker pose estimation

## Why It Fits

Essential for autonomous charging and teaches visual servoing fundamentals.

## ROS 2 Integration

```python
# Node structure:
# Subscribes: /camera/color/image_raw, /odom
# Publishes: /cmd_vel, /docking_status
# Services: /dock (trigger docking), /undock
# Uses: cv_bridge, apriltag_ros or custom ArUco detection
```

## Implementation Details

### AprilTag Detection

AprilTags are robust fiducial markers designed for precise pose estimation:

```python
import cv2
from dt_apriltags import Detector

class DockingNode(Node):
    def __init__(self):
        super().__init__('docking_node')

        # Initialize AprilTag detector
        self.detector = Detector(
            families='tag36h11',
            nthreads=4,
            quad_decimate=2.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
        )

        # Camera intrinsics (from RealSense calibration)
        self.camera_params = [
            fx, fy, cx, cy  # Focal lengths and principal point
        ]

        # Docking state machine
        self.state = 'IDLE'  # IDLE, APPROACH, ALIGN, DOCK, DOCKED
```

### Visual Servoing Control

```python
def visual_servo(self, marker_pose):
    """
    Convert marker pose to velocity commands for docking
    """
    twist = Twist()

    # Extract position error
    dx = marker_pose.translation[0]  # Lateral error
    dy = marker_pose.translation[1]  # Vertical error (depth)
    dz = marker_pose.translation[2]  # Forward distance

    # Extract orientation error (yaw)
    rotation_matrix = marker_pose.rotation
    yaw_error = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])

    # Proportional control gains
    Kp_linear = 0.3
    Kp_angular = 0.5

    # Generate velocity commands
    # Use mecanum strafing for lateral alignment
    twist.linear.y = -Kp_linear * dx
    twist.linear.x = Kp_linear * (dz - target_distance)
    twist.angular.z = Kp_angular * yaw_error

    # Thresholds for completion
    if abs(dx) < 0.02 and abs(dz - target_distance) < 0.05 and abs(yaw_error) < 0.1:
        self.state = 'DOCKED'
        twist = Twist()  # Stop

    return twist
```

### State Machine

```python
def docking_state_machine(self):
    """
    Finite state machine for docking sequence
    """
    if self.state == 'IDLE':
        # Wait for dock command
        pass

    elif self.state == 'APPROACH':
        # Navigate to approximate docking zone using Nav2
        if self.distance_to_dock < 1.0:
            self.state = 'ALIGN'

    elif self.state == 'ALIGN':
        # Switch to visual servoing
        if self.marker_detected:
            twist = self.visual_servo(self.marker_pose)
            self.cmd_vel_pub.publish(twist)
        else:
            # Search for marker
            self.search_for_marker()

    elif self.state == 'DOCK':
        # Final precise alignment
        twist = self.visual_servo(self.marker_pose)
        self.cmd_vel_pub.publish(twist)

    elif self.state == 'DOCKED':
        # Verify electrical connection
        self.publish_docking_status('DOCKED')
```

## Hardware Setup

### AprilTag Marker Placement

1. Print AprilTag marker (tag36h11 family recommended)
2. Mount on docking station at known height (e.g., 20cm from ground)
3. Ensure good lighting and no reflective surfaces nearby
4. Marker should be visible from 0.5-2.0m away

### Docking Station Design

```
     [AprilTag Marker]
            |
    ┌───────┴────────┐
    │  Charging Pins  │
    │   [+ -]         │
    └────────────────┘
```

## Configuration Parameters

```yaml
docking_params:
  marker_id: 0  # AprilTag ID for docking station
  target_distance: 0.15  # meters from marker
  approach_distance: 1.0  # Switch to visual servoing

  # Control gains
  kp_linear: 0.3
  kp_angular: 0.5

  # Tolerances
  position_tolerance: 0.02  # meters
  angle_tolerance: 0.1  # radians

  # Safety limits
  max_approach_speed: 0.2  # m/s
  timeout: 30.0  # seconds
```

## Testing Procedure

1. **Marker Detection Test**
   ```bash
   ros2 run orbibot_ai test_apriltag_detection
   ```

2. **Manual Alignment Test**
   - Position robot 1m from marker
   - Verify marker detection and pose estimation
   - Check velocity commands are reasonable

3. **Full Docking Test**
   ```bash
   ros2 service call /dock std_srvs/srv/Trigger
   ```

4. **Undocking Test**
   ```bash
   ros2 service call /undock std_srvs/srv/Trigger
   ```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Marker not detected | Poor lighting, distance | Adjust lighting, move closer |
| Oscillating approach | Gains too high | Reduce Kp values |
| Fails to align | Camera calibration off | Re-calibrate camera intrinsics |
| Slow convergence | Gains too low | Increase Kp values |

## Hardware Requirements

| Component | Cost | Notes |
|-----------|------|-------|
| AprilTag Markers | $5-10 | Print on cardstock or laminate |
| Charging contacts | $20-50 | Pogo pins or magnetic connector |

---

[← Previous: Visual Tracking](01-visual-tracking.md) | [↑ Index](README.md) | [Next: Voice Control →](03-voice-control.md)
