# 14. Self-Debugging Robot with Log Analysis

**Difficulty:** Moderate
**Category:** Autonomy & Reliability
**Why it's unique:** Robot explains its own failures
**Prerequisites:** Feature #13 (MCP integration)

## Description

Create a system where failures trigger automatic analysis using Claude, enabling the robot to understand and explain its own malfunctions.

## Implementation

```python
#!/usr/bin/env python3
"""
Self-Debugging Agent
Monitors robot health and analyzes failures using Claude
"""

import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import DiagnosticArray
from nav_msgs.msg import Odometry
import subprocess
import json
from datetime import datetime, timedelta

class RobotDebugAgent(Node):
    def __init__(self):
        super().__init__('robot_debug_agent')

        # Failure detection
        self.create_subscription(
            DiagnosticArray, '/diagnostics',
            self.diagnostics_callback, 10)

        self.create_subscription(
            Odometry, '/odom',
            self.odom_callback, 10)

        # State tracking
        self.last_odom_time = None
        self.navigation_failures = []
        self.diagnostics_errors = []

        # Recording
        self.is_recording = False
        self.bag_process = None

        self.get_logger().info('Self-debugging agent active')

    def diagnostics_callback(self, msg):
        """Monitor diagnostic messages for errors."""
        for status in msg.status:
            if status.level >= 2:  # ERROR or STALE
                self.handle_diagnostic_error(status)

    def odom_callback(self, msg):
        """Detect odometry anomalies."""
        now = self.get_clock().now()

        if self.last_odom_time is not None:
            dt = (now - self.last_odom_time).nanoseconds / 1e9

            # Detect excessive latency
            if dt > 0.5:
                self.handle_odometry_issue({
                    'type': 'latency',
                    'value': dt,
                    'timestamp': now
                })

        self.last_odom_time = now

    async def handle_diagnostic_error(self, status):
        """Analyze diagnostic error using Claude."""
        self.get_logger().error(f'Diagnostic error: {status.name} - {status.message}')

        # Start recording if not already
        if not self.is_recording:
            await self.start_recording()

        # Collect context
        context = await self.collect_failure_context(status.name)

        # Analyze with Claude (via MCP)
        analysis = await self.analyze_with_claude(
            failure_type='diagnostic_error',
            failure_name=status.name,
            failure_message=status.message,
            context=context
        )

        # Log analysis
        self.get_logger().info(f'Claude analysis: {analysis["summary"]}')

        # Auto-fix if possible
        if analysis.get('auto_fix_available'):
            self.get_logger().info('Attempting auto-fix...')
            await self.apply_fix(analysis['suggested_fixes'][0])

    async def collect_failure_context(self, failure_name: str) -> dict:
        """Collect comprehensive context about the failure."""
        context = {}

        # Recent logs
        context['logs'] = subprocess.check_output([
            'journalctl', '-u', 'orbibot.service',
            '--since', '1 minute ago',
            '--lines=100'
        ]).decode('utf-8')

        # TF tree
        context['tf_tree'] = subprocess.check_output([
            'ros2', 'run', 'tf2_tools', 'view_frames',
            '--timeout', '2'
        ]).decode('utf-8')

        # Node graph
        context['nodes'] = subprocess.check_output([
            'ros2', 'node', 'list'
        ]).decode('utf-8')

        # Topic hz
        context['topic_rates'] = {}
        for topic in ['/odom', '/scan', '/orbibot/encoders']:
            try:
                hz_output = subprocess.check_output([
                    'timeout', '2',
                    'ros2', 'topic', 'hz', topic
                ], timeout=3).decode('utf-8')
                context['topic_rates'][topic] = hz_output
            except:
                context['topic_rates'][topic] = 'TIMEOUT'

        # System resources
        context['resources'] = {
            'cpu': subprocess.check_output(['top', '-bn1']).decode('utf-8'),
            'memory': subprocess.check_output(['free', '-h']).decode('utf-8'),
            'disk': subprocess.check_output(['df', '-h']).decode('utf-8'),
        }

        # If bag recording was active, include snippet
        if self.is_recording:
            context['bag_path'] = f'/tmp/debug_{failure_name}_{datetime.now().timestamp()}.db3'
            await self.stop_recording(context['bag_path'])

        return context

    async def analyze_with_claude(self, failure_type, failure_name,
                                   failure_message, context) -> dict:
        """Send failure context to Claude for analysis via MCP."""

        prompt = f"""
        🔍 Robot Failure Analysis Request

        **Failure Type:** {failure_type}
        **Component:** {failure_name}
        **Error Message:** {failure_message}
        **Timestamp:** {datetime.now().isoformat()}

        **Context:**

        ### Recent Logs
        ```
        {context['logs'][-1000:]}  # Last 1000 chars
        ```

        ### TF Tree Status
        ```
        {context['tf_tree']}
        ```

        ### Active Nodes
        ```
        {context['nodes']}
        ```

        ### Topic Rates
        ```json
        {json.dumps(context['topic_rates'], indent=2)}
        ```

        ### System Resources
        CPU: {context['resources']['cpu'][:200]}
        Memory: {context['resources']['memory']}

        Please analyze this failure and provide:
        1. Root cause analysis
        2. Contributing factors
        3. Suggested fixes (in priority order)
        4. Whether auto-fix is possible
        5. Prevention strategies

        Format your response as JSON.
        """

        # Call Claude via MCP (implementation depends on MCP setup)
        # This is a simplified example
        response = await self.call_claude_mcp(prompt)

        return response

    async def start_recording(self):
        """Start recording ROS bag for failure analysis."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bag_name = f'/tmp/debug_{timestamp}'

        self.bag_process = subprocess.Popen([
            'ros2', 'bag', 'record',
            '-o', bag_name,
            '/odom', '/scan', '/cmd_vel', '/tf', '/diagnostics',
            '--max-bag-duration', '30'  # 30 seconds max
        ])

        self.is_recording = True
        self.get_logger().info(f'Started recording bag: {bag_name}')

    async def stop_recording(self, output_path: str = None):
        """Stop bag recording."""
        if self.bag_process:
            self.bag_process.terminate()
            self.bag_process.wait()
            self.is_recording = False
            self.get_logger().info('Stopped recording bag')

    async def apply_fix(self, fix: dict):
        """Attempt to automatically apply a suggested fix."""
        fix_type = fix['type']

        if fix_type == 'restart_node':
            node_name = fix['node']
            subprocess.run(['ros2', 'lifecycle', 'set', node_name, 'deactivate'])
            subprocess.run(['ros2', 'lifecycle', 'set', node_name, 'activate'])
            self.get_logger().info(f'Restarted node: {node_name}')

        elif fix_type == 'update_parameter':
            node = fix['node']
            param = fix['parameter']
            value = fix['value']
            subprocess.run([
                'ros2', 'param', 'set', node, param, str(value)
            ])
            self.get_logger().info(f'Updated parameter: {node}/{param}={value}')

        elif fix_type == 'clear_costmap':
            subprocess.run([
                'ros2', 'service', 'call',
                '/global_costmap/clear_entirely_global_costmap',
                'std_srvs/srv/Empty'
            ])
            self.get_logger().info('Cleared global costmap')

        else:
            self.get_logger().warn(f'Unknown fix type: {fix_type}')

def main():
    rclpy.init()
    node = RobotDebugAgent()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Example Output

```
🔍 Failure Analysis: Navigation timeout at (2.3, 1.5)

Root cause: TF transform odom→base_footprint had 0.3s latency spike
Contributing factors:
  - control_manager CPU usage spiked to 95%
  - IMU callback queue backed up (12 pending)
  - Network multicast storm detected (500+ packets/sec)

Suggested fixes:
  1. [AUTO] Increase control_manager thread priority
     Command: sudo renice -n -5 -p <pid>

  2. [MANUAL] Add TF timeout handling in nav2_params.yaml
     Change: transform_timeout: 0.1 → 0.5

  3. [AUTO] Reduce IMU publish rate
     Command: ros2 param set /hardware_node imu_rate 30

  4. [MANUAL] Isolate ROS traffic to dedicated network interface
     Add: ROS_DOMAIN_ID=1, use DDS unicast configuration

Prevention strategies:
  - Monitor TF latency continuously
  - Add watchdog for control_manager CPU usage
  - Implement graceful degradation on sensor delays

Shall I apply fix #1 (increase thread priority)? [Y/n]
```

## Integration with Alerts

```python
class AlertManager:
    """Send alerts when critical failures occur."""

    def __init__(self, config):
        self.email_config = config['email']
        self.mqtt_client = config.get('mqtt')

    async def send_alert(self, severity: str, summary: str,
                        analysis: dict):
        """Send multi-channel alert."""

        if severity == 'critical':
            # Email
            await self.send_email(
                subject=f'🚨 OrbiBot Critical Failure: {summary}',
                body=self.format_analysis(analysis)
            )

            # MQTT (for home automation)
            if self.mqtt_client:
                self.mqtt_client.publish(
                    'orbibot/alerts/critical',
                    json.dumps(analysis)
                )

            # Push notification (optional)
            await self.send_push_notification(summary)
```

---

[← Previous: MCP Integration](13-mcp-integration.md) | [↑ Index](README.md) | [Next: Sim2Real Bridge →](15-sim2real.md)
