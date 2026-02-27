#!/usr/bin/env python3
"""
System Monitor Node
Subscribes to /orbibot/system_status from hardware_node and enriches it with CPU/RAM/temp/disk metrics
"""

import copy
import rclpy
from rclpy.node import Node
from orbibot_msgs.msg import SystemStatus
import psutil


class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__('system_monitor')
        
        # Publisher
        self.status_publisher = self.create_publisher(
            SystemStatus,
            '/orbibot/system_status_enriched',
            10
        )
        
        # Subscriber to hardware status (matches hardware_node publish topic)
        self.hardware_status_sub = self.create_subscription(
            SystemStatus,
            '/orbibot/system_status',
            self.hardware_status_callback,
            10
        )
        
        # Store last hardware status
        self.last_hardware_status = None
        
        # Timer for periodic publishing (1 Hz)
        self.timer = self.create_timer(1.0, self.publish_enriched_status)
        
        self.get_logger().info('System Monitor Node started - enriching /system_status')
    
    def hardware_status_callback(self, msg):
        """Store hardware status for merging"""
        self.last_hardware_status = msg
    
    def get_cpu_temperature(self):
        """Get CPU temperature (Raspberry Pi specific)"""
        try:
            # Try to read from thermal zone (works on Raspberry Pi)
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except (FileNotFoundError, ValueError, PermissionError):
            # Fallback: try psutil sensors (may not work on all systems)
            try:
                temps = psutil.sensors_temperatures()
                if 'cpu_thermal' in temps:
                    return temps['cpu_thermal'][0].current
                elif 'coretemp' in temps:
                    return temps['coretemp'][0].current
            except (AttributeError, KeyError, IndexError):
                pass
        return 0.0
    
    def publish_enriched_status(self):
        """Publish enriched system status message"""
        # Start with hardware data if available, otherwise create new
        if self.last_hardware_status:
            msg = copy.deepcopy(self.last_hardware_status)
        else:
            msg = SystemStatus()
            msg.battery_voltage = 0.0
            msg.motors_enabled = False
            msg.emergency_stop = False
            msg.hardware_ok = False
        
        # Update header
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ''
        
        # Enrich with system resources
        msg.cpu_percent = psutil.cpu_percent(interval=0.1)
        msg.ram_percent = psutil.virtual_memory().percent
        msg.cpu_temp = self.get_cpu_temperature()
        msg.disk_percent = psutil.disk_usage('/').percent
        
        self.status_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
