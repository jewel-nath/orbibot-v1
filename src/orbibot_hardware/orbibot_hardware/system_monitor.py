#!/usr/bin/env python3
"""
System Monitor Node
Subscribes to /orbibot/system_status from hardware_node and enriches it with CPU/RAM/temp/disk metrics
"""

import copy
import glob
import os
import rclpy
from rclpy.node import Node
from orbibot_msgs.msg import SystemStatus
import psutil

# hwmon driver names that expose a CPU package temperature, most specific
# first. k10temp is AMD (Ryzen), coretemp is Intel, cpu_thermal is the
# Raspberry Pi's. Anything else on a board is a different chip entirely.
CPU_HWMON_NAMES = ('k10temp', 'coretemp', 'cpu_thermal')

# Substrings that mark a /sys/class/thermal zone as belonging to the CPU.
CPU_THERMAL_ZONE_TYPES = ('x86_pkg_temp', 'cpu-thermal', 'cpu_thermal', 'acpitz')


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
        
        # P1: Seed CPU baseline once; then use interval=None to avoid blocking 100ms per cycle
        self._cpu_seeded = False
        
        # Timer for periodic publishing (1 Hz)
        self.timer = self.create_timer(1.0, self.publish_enriched_status)
        
        self.get_logger().info('System Monitor Node started - enriching /system_status')
    
    def hardware_status_callback(self, msg):
        """Store hardware status for merging"""
        self.last_hardware_status = msg
    
    def get_cpu_temperature(self):
        """
        Read the CPU package temperature in degrees Celsius.

        Identifies the sensor by name rather than by position. The previous
        implementation read `thermal_zone0` unconditionally, which was the CPU
        on the Raspberry Pi but is the WiFi adapter (`iwlwifi_1`) on the
        Beelink — so it reported a plausible-looking number from the wrong
        chip. A wrong temperature is worse than no temperature, because
        nothing downstream can tell it is wrong.

        Returns:
            Temperature in °C, or 0.0 if no CPU sensor could be identified.
        """
        temp = self._read_hwmon_cpu_temp()
        if temp is not None:
            return temp

        temp = self._read_thermal_zone_cpu_temp()
        if temp is not None:
            return temp

        # Last resort. psutil groups by the same driver names, so this mostly
        # matters when sysfs is not readable.
        try:
            temps = psutil.sensors_temperatures()
            for name in CPU_HWMON_NAMES:
                if temps.get(name):
                    return temps[name][0].current
        except (AttributeError, KeyError, IndexError):
            pass

        return 0.0

    def _read_hwmon_cpu_temp(self):
        """
        Find a CPU temperature via /sys/class/hwmon, matched by driver name.

        Returns:
            Temperature in °C, or None if no known CPU driver is present.
        """
        for name in CPU_HWMON_NAMES:
            for hwmon_dir in glob.glob('/sys/class/hwmon/hwmon*'):
                try:
                    with open(os.path.join(hwmon_dir, 'name'), 'r') as f:
                        if f.read().strip() != name:
                            continue
                    inputs = sorted(glob.glob(os.path.join(hwmon_dir, 'temp*_input')))
                    if not inputs:
                        continue
                    with open(inputs[0], 'r') as f:
                        return float(f.read().strip()) / 1000.0
                except (FileNotFoundError, ValueError, PermissionError, OSError):
                    continue
        return None

    def _read_thermal_zone_cpu_temp(self):
        """
        Find a CPU temperature via /sys/class/thermal, matched by zone type.

        Checks each zone's `type` before trusting its `temp`. Zone ordering is
        not stable across machines and carries no meaning.

        Returns:
            Temperature in °C, or None if no zone looks like a CPU.
        """
        for zone_dir in sorted(glob.glob('/sys/class/thermal/thermal_zone*')):
            try:
                with open(os.path.join(zone_dir, 'type'), 'r') as f:
                    zone_type = f.read().strip().lower()
                if not any(t in zone_type for t in CPU_THERMAL_ZONE_TYPES):
                    continue
                with open(os.path.join(zone_dir, 'temp'), 'r') as f:
                    return float(f.read().strip()) / 1000.0
            except (FileNotFoundError, ValueError, PermissionError, OSError):
                continue
        return None
    
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
        
        # Enrich with system resources (P1: interval=None after first seed — non-blocking)
        if not self._cpu_seeded:
            msg.cpu_percent = psutil.cpu_percent(interval=0.1)
            self._cpu_seeded = True
        else:
            msg.cpu_percent = psutil.cpu_percent(interval=None)
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
