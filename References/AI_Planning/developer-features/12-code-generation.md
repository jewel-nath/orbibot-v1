# 12. Code Generation Agent for ROS2

**Difficulty:** Moderate
**Category:** Code Automation
**Why it's unique:** Describe nodes in English, get working code
**Prerequisites:** Feature #11 (development hooks)

## Description

Natural language to ROS2 code generation with full integration. Dramatically reduces boilerplate and accelerates feature development.

## What Can Be Generated

| Request Type | Generated Output | Time Saved |
|--------------|------------------|------------|
| Simple subscriber node | Full .py + launch + package.xml update | 15-30 min |
| Vision processing node | cv_bridge integration + OpenCV processing | 30-60 min |
| Custom message definition | .msg file + CMake + code generation | 10-20 min |
| Nav2 behavior tree | XML tree + plugin code | 45-90 min |
| Launch file | Multi-node orchestration + params | 20-40 min |
| Diagnostic node | System monitoring + alerts | 30-60 min |

## Example 1: ArUco Marker Detector

**Your prompt:**
```
Create a node that subscribes to the camera, detects ArUco markers,
and publishes their poses as TF transforms. Use marker ID as frame name.
```

**Claude generates:**

```python
#!/usr/bin/env python3
"""
ArUco Marker Detection Node
Detects ArUco markers and broadcasts their poses as TF transforms.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import TransformStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
from tf2_ros import TransformBroadcaster

class ArucoDetectorNode(Node):
    def __init__(self):
        super().__init__('aruco_detector')

        # Parameters
        self.declare_parameter('marker_size', 0.15)  # meters
        self.declare_parameter('dictionary', 'DICT_4X4_50')
        self.declare_parameter('camera_frame', 'camera_link')

        self.marker_size = self.get_parameter('marker_size').value
        dict_name = self.get_parameter('dictionary').value
        self.camera_frame = self.get_parameter('camera_frame').value

        # ArUco setup
        aruco_dict = getattr(cv2.aruco, dict_name)
        self.dictionary = cv2.aruco.getPredefinedDictionary(aruco_dict)
        self.parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)

        # ROS setup
        self.bridge = CvBridge()
        self.tf_broadcaster = TransformBroadcaster(self)

        self.camera_matrix = None
        self.dist_coeffs = None

        # Subscribers
        self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10)
        self.create_subscription(
            CameraInfo, '/camera/color/camera_info',
            self.camera_info_callback, 10)

        self.get_logger().info('ArUco detector node started')

    def camera_info_callback(self, msg):
        """Store camera calibration parameters."""
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.dist_coeffs = np.array(msg.d)
            self.get_logger().info('Camera calibration received')

    def image_callback(self, msg):
        """Detect ArUco markers and publish TF transforms."""
        if self.camera_matrix is None:
            return

        # Convert ROS Image to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect markers
        corners, ids, _ = self.detector.detectMarkers(gray)

        if ids is not None:
            # Estimate pose for each marker
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, self.marker_size,
                self.camera_matrix, self.dist_coeffs)

            for i, marker_id in enumerate(ids.flatten()):
                # Create TF transform
                t = TransformStamped()
                t.header.stamp = msg.header.stamp
                t.header.frame_id = self.camera_frame
                t.child_frame_id = f'aruco_{marker_id}'

                # Translation
                t.transform.translation.x = float(tvecs[i][0][0])
                t.transform.translation.y = float(tvecs[i][0][1])
                t.transform.translation.z = float(tvecs[i][0][2])

                # Rotation (convert from rodrigues to quaternion)
                rotation_matrix, _ = cv2.Rodrigues(rvecs[i][0])
                quat = self.rotation_matrix_to_quaternion(rotation_matrix)
                t.transform.rotation.x = quat[0]
                t.transform.rotation.y = quat[1]
                t.transform.rotation.z = quat[2]
                t.transform.rotation.w = quat[3]

                # Broadcast transform
                self.tf_broadcaster.sendTransform(t)

    @staticmethod
    def rotation_matrix_to_quaternion(R):
        """Convert 3x3 rotation matrix to quaternion."""
        trace = np.trace(R)
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        else:
            if R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
                s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
                w = (R[2, 1] - R[1, 2]) / s
                x = 0.25 * s
                y = (R[0, 1] + R[1, 0]) / s
                z = (R[0, 2] + R[2, 0]) / s
            elif R[1, 1] > R[2, 2]:
                s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
                w = (R[0, 2] - R[2, 0]) / s
                x = (R[0, 1] + R[1, 0]) / s
                y = 0.25 * s
                z = (R[1, 2] + R[2, 1]) / s
            else:
                s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
                w = (R[1, 0] - R[0, 1]) / s
                x = (R[0, 2] + R[2, 0]) / s
                y = (R[1, 2] + R[2, 1]) / s
                z = 0.25 * s
        return np.array([x, y, z, w])

def main(args=None):
    rclpy.init(args=args)
    node = ArucoDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

**Also generates launch file:**

```python
# launch/aruco_detector.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='orbibot_ai',
            executable='aruco_detector',
            name='aruco_detector',
            parameters=[{
                'marker_size': 0.15,  # 15cm markers
                'dictionary': 'DICT_4X4_50',
                'camera_frame': 'camera_link',
            }],
            remappings=[
                ('/camera/color/image_raw', '/camera/color/image_raw'),
                ('/camera/color/camera_info', '/camera/color/camera_info'),
            ]
        ),
    ])
```

**And updates package.xml:**
```xml
<depend>cv_bridge</depend>
<depend>sensor_msgs</depend>
<depend>geometry_msgs</depend>
<depend>tf2_ros</depend>
```

## Example 2: Battery Monitor with Alerts

**Your prompt:**
```
Create a battery monitoring node that subscribes to battery voltage,
publishes battery percentage, and sends email alerts when below 20%.
Include a service to get battery health status.
```

**Claude generates the complete implementation** including:
- ROS 2 node with battery state estimation
- Email alert integration (SMTP)
- Custom service definition
- Launch file with parameters
- Configuration file for alert thresholds

## Example 3: Autonomous Docking Behavior

**Your prompt:**
```
Create a visual docking behavior that:
1. Searches for an AprilTag (ID 10) by rotating
2. Approaches the tag to 30cm distance
3. Aligns to face the tag directly
4. Moves forward slowly until contact
5. Publishes docking status throughout
```

Claude generates a state machine implementation with proper error handling and recovery.

## Integration with Your Workflow

```yaml
# .claude/hooks.yaml
hooks:
  custom_commands:
    /gen-node:
      description: "Generate ROS2 node from description"
      command: |
        echo "Describe the node you want to create:"
        # Claude will prompt for description and generate code
```

## Best Practices for Code Generation Prompts

**Good prompts are:**
- **Specific**: "Subscribe to /camera/image, detect red objects, publish centroids"
- **Include constraints**: "Must run at 30Hz, use OpenCV, avoid GPU"
- **Mention integration points**: "Should work with existing Nav2 stack"
- **Specify error handling**: "Retry 3 times on failure, then alert user"

**Examples:**

✅ **Good:**
```
Create a lidar-based obstacle detector that:
- Subscribes to /scan (sensor_msgs/LaserScan)
- Detects objects within 0.5m in front of robot
- Publishes Bool on /obstacle_detected
- Uses 30-degree cone in front direction
- Publishes at 10Hz
```

❌ **Too vague:**
```
Make an obstacle detector
```

## Time Savings Estimate

| Task | Manual Time | With AI Generation | Time Saved |
|------|-------------|-------------------|------------|
| Simple publisher/subscriber | 30 min | 2 min | 93% |
| Vision processing node | 2 hours | 10 min | 92% |
| Custom service definition | 45 min | 3 min | 93% |
| Launch file with 5+ nodes | 1 hour | 5 min | 92% |
| Behavior tree implementation | 3 hours | 20 min | 89% |

**Average time savings: ~90%** on boilerplate code

---

[← Previous: Development Hooks](11-hooks-and-commands.md) | [↑ Index](README.md) | [Next: MCP Integration →](13-mcp-integration.md)
