# 11. Claude Code Development Hooks for ROS2

**Difficulty:** Easy/Moderate
**Category:** Developer Productivity
**Why it's unique:** Accelerates YOUR development workflow
**Prerequisites:** None

## Description

Create custom Claude Code hooks that integrate with your robot development workflow, enabling hot-reload, automated testing, and robot-aware commands.

## Hook Types Available

### 1. Post-File-Save Hooks
Automatically trigger actions when files are saved:

```yaml
# .claude/hooks.yaml
hooks:
  post_file_save:
    # Hot reload Python nodes without restarting
    - pattern: "src/orbibot_*/orbibot_*/**/*.py"
      command: |
        pkill -HUP -f "$(basename $FILE .py)" || echo "Node not running"

    # Rebuild firmware on config changes
    - pattern: "src/orbibot_rosmaster_firmware/include/orbibot_config.h"
      command: |
        cd src/orbibot_rosmaster_firmware && \
        ~/.platformio/penv/bin/pio run

    # Auto-format Python code
    - pattern: "src/**/*.py"
      command: "black $FILE --line-length 100"

    # Update launch files when configs change
    - pattern: "src/**/config/*.yaml"
      command: |
        echo "Config changed: $FILE"
        ros2 param load /hardware_node $FILE || true
```

### 2. Custom Slash Commands

Create robot-specific commands accessible via `/command` in Claude Code:

```yaml
# .claude/hooks.yaml
hooks:
  custom_commands:
    # Quick status check
    /robot-status:
      description: "Get comprehensive robot status"
      command: |
        echo "=== OrbiBot System Status ===" && \
        ros2 topic echo /orbibot/system_status --once && \
        echo "\n=== Battery ===" && \
        ros2 topic echo /orbibot/battery --once && \
        echo "\n=== Active Nodes ===" && \
        ros2 node list

    # Real-time logs with context
    /robot-logs:
      description: "Stream robot logs (last 50 lines + follow)"
      command: "journalctl -u orbibot.service -f --lines=50"

    # Motor diagnostics
    /test-motors:
      description: "Run motor diagnostic sequence"
      command: |
        python3 src/orbibot_rosmaster_firmware/tests/test_motor_speed.py \
        --port /dev/motordriver

    # Emergency stop
    /estop:
      description: "Emergency stop all motors"
      command: |
        ros2 topic pub --once /cmd_vel geometry_msgs/Twist \
        "{linear: {x: 0, y: 0, z: 0}, angular: {x: 0, y: 0, z: 0}}"

    # Quick encoder check
    /check-encoders:
      description: "Display encoder values in real-time"
      command: "ros2 topic echo /orbibot/encoders --once"

    # IMU calibration
    /calibrate-imu:
      description: "Run IMU calibration procedure"
      command: |
        python3 src/orbibot_hardware/scripts/calibrate_imu.py && \
        echo "Restart hardware_node to apply calibration"

    # Network diagnostics
    /net-check:
      description: "Check ROS 2 DDS discovery and network health"
      command: |
        ros2 doctor --report && \
        ros2 daemon status
```

### 3. Pre-Commit Validation Hooks

Ensure code quality before commits:

```yaml
hooks:
  pre_commit:
    # Run tests before allowing commit
    - command: |
        source install/setup.bash && \
        colcon test --packages-select orbibot_hardware orbibot_control && \
        colcon test-result --verbose

    # Check firmware builds
    - command: |
        cd src/orbibot_rosmaster_firmware && \
        ~/.platformio/penv/bin/pio run

    # Lint Python code
    - command: "ruff check src/"

    # Verify URDF validity
    - command: |
        check_urdf src/orbibot_description/urdf/orbibot.urdf.xacro
```

## Advanced Custom Commands

### `/robot-diag` - Comprehensive Diagnostic with AI Analysis

```bash
#!/bin/bash
# .claude/scripts/robot_diag.sh

OUTPUT_FILE="/tmp/robot_diagnostic_$(date +%s).txt"

{
    echo "=== ORBIBOT COMPREHENSIVE DIAGNOSTIC ==="
    echo "Timestamp: $(date)"
    echo ""

    echo "=== ROS 2 Node Health ==="
    ros2 node list
    echo ""

    echo "=== Topic Hz Check ==="
    timeout 3 ros2 topic hz /odom &
    timeout 3 ros2 topic hz /orbibot/encoders &
    timeout 3 ros2 topic hz /scan &
    wait
    echo ""

    echo "=== TF Tree Status ==="
    ros2 run tf2_tools view_frames --timeout 5
    echo ""

    echo "=== Hardware Node Parameters ==="
    ros2 param dump /hardware_node
    echo ""

    echo "=== System Resources ==="
    echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
    echo "Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
    echo "Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
    echo ""

    echo "=== Recent Errors ==="
    journalctl -u orbibot.service --since "5 minutes ago" | grep -i error
    echo ""

    echo "=== Motor Status ==="
    python3 src/orbibot_rosmaster_firmware/tests/test_connection.py --port /dev/motordriver
    echo ""

} | tee "$OUTPUT_FILE"

echo ""
echo "Full diagnostic saved to: $OUTPUT_FILE"
echo ""
echo "Claude, please analyze the above diagnostic output and identify any issues."
```

Then in hooks.yaml:
```yaml
/robot-diag:
  description: "Run comprehensive diagnostic with AI analysis"
  command: "bash .claude/scripts/robot_diag.sh"
```

### `/replay-bag` - ROS Bag Analysis with AI Narration

```yaml
/replay-bag:
  description: "Replay ROS bag and extract key events"
  command: |
    BAG_FILE="$1"
    ros2 bag info "$BAG_FILE"
    echo "\n=== Replaying bag with topic summary ==="
    ros2 bag play "$BAG_FILE" --topics /odom /scan /cmd_vel --rate 2
```

Claude can then analyze the replayed data and narrate what happened during that recording.

### `/tune-pid` - AI-Assisted PID Tuning

```python
#!/usr/bin/env python3
# .claude/scripts/tune_pid.py

import rclpy
from rclpy.node import Node
from orbibot_msgs.msg import EncoderStamped
import numpy as np
import matplotlib.pyplot as plt

class PIDTuner(Node):
    def __init__(self):
        super().__init__('pid_tuner')
        self.encoder_data = []
        self.sub = self.create_subscription(
            EncoderStamped, '/orbibot/encoders',
            self.encoder_callback, 10)

    def encoder_callback(self, msg):
        self.encoder_data.append({
            'time': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'fl': msg.front_left,
            'fr': msg.front_right,
            'bl': msg.back_left,
            'br': msg.back_right,
        })

    def analyze_response(self):
        # Convert to numpy arrays
        times = np.array([d['time'] for d in self.encoder_data])
        fl_counts = np.array([d['fl'] for d in self.encoder_data])

        # Calculate metrics
        rise_time = self.calculate_rise_time(times, fl_counts)
        overshoot = self.calculate_overshoot(fl_counts)
        settling_time = self.calculate_settling_time(times, fl_counts)

        print(f"\n=== PID Response Analysis ===")
        print(f"Rise Time: {rise_time:.3f}s")
        print(f"Overshoot: {overshoot:.1f}%")
        print(f"Settling Time: {settling_time:.3f}s")

        # Plot response
        plt.plot(times, fl_counts)
        plt.xlabel('Time (s)')
        plt.ylabel('Encoder Counts')
        plt.title('Motor Step Response')
        plt.savefig('/tmp/pid_response.png')
        print(f"\nResponse plot saved to /tmp/pid_response.png")

        # Suggestions based on metrics
        print(f"\n=== Tuning Suggestions ===")
        if overshoot > 20:
            print("⚠ High overshoot detected - consider reducing Kp or increasing Kd")
        if rise_time > 1.0:
            print("⚠ Slow rise time - consider increasing Kp")
        if settling_time > 2.0:
            print("⚠ Long settling time - consider increasing Ki")

        return {
            'rise_time': rise_time,
            'overshoot': overshoot,
            'settling_time': settling_time,
            'plot_path': '/tmp/pid_response.png'
        }

def main():
    rclpy.init()
    tuner = PIDTuner()

    print("Collecting encoder data for 5 seconds...")
    print("Please command the robot to move forward now.")

    # Collect data
    import time
    start = time.time()
    while time.time() - start < 5.0:
        rclpy.spin_once(tuner, timeout_sec=0.1)

    # Analyze
    results = tuner.analyze_response()

    tuner.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Benefits

1. **Faster Iteration** - No manual rebuild/restart cycles
2. **Robot-Aware Context** - Claude understands your robot's state
3. **Automated Diagnostics** - AI identifies issues from logs/data
4. **Seamless Workflow** - Stay in coding flow without context switching

## Setup Instructions

```bash
# 1. Create hooks configuration
mkdir -p .claude
cat > .claude/hooks.yaml << 'EOF'
# Your hooks configuration here
EOF

# 2. Create custom scripts directory
mkdir -p .claude/scripts

# 3. Make scripts executable
chmod +x .claude/scripts/*.sh .claude/scripts/*.py

# 4. Test a custom command
# (In Claude Code): /robot-status
```

---

[← Back to Index](README.md) | [Next: Code Generation →](12-code-generation.md)
