"""Firmware commands — PID, beep, calibration, reset, version query."""

import logging
from typing import Any, Dict, Optional

from std_msgs.msg import Float32MultiArray, UInt16

logger = logging.getLogger(__name__)


class FirmwareMixin:
    """Firmware configuration and command methods.

    Publishes to /orbibot/* topics and calls orbibot_msgs services for
    PID tuning, buzzer control, odometry/encoder reset, and IMU calibration.
    """

    def _init_firmware(self):
        """Create firmware publishers. Called by RosBridge.__init__."""
        self._pid_params_pub = self._node.create_publisher(
            Float32MultiArray, '/orbibot/pid_params', 10)
        self._yaw_pid_params_pub = self._node.create_publisher(
            Float32MultiArray, '/orbibot/yaw_pid_params', 10)
        self._pid_save_pub = self._node.create_publisher(
            Float32MultiArray, '/orbibot/pid_save', 10)
        self._yaw_pid_save_pub = self._node.create_publisher(
            Float32MultiArray, '/orbibot/yaw_pid_save', 10)
        self._beep_pub = self._node.create_publisher(UInt16, '/orbibot/beep', 10)

    # -- PID --

    def set_motor_pid(self, kp: float, ki: float, kd: float) -> None:
        """Set motor PID gains (all wheels). Takes effect immediately."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._pid_params_pub.publish(msg)
        logger.info(f'Published motor PID: kp={kp}, ki={ki}, kd={kd}')

    def set_yaw_pid(self, kp: float, ki: float, kd: float) -> None:
        """Set yaw (heading) PID gains. Takes effect immediately."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._yaw_pid_params_pub.publish(msg)
        logger.info(f'Published yaw PID: kp={kp}, ki={ki}, kd={kd}')

    def save_motor_pid(self, kp: float, ki: float, kd: float) -> Dict[str, Any]:
        """Save motor PID gains to firmware flash (persists across reboot)."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._pid_save_pub.publish(msg)
        logger.info(f'Published motor PID save: kp={kp}, ki={ki}, kd={kd}')
        return {'status': 'ok', 'motor_pid_saved': {'kp': kp, 'ki': ki, 'kd': kd},
                'note': 'Gains written to firmware flash — will persist after reboot'}

    def save_yaw_pid(self, kp: float, ki: float, kd: float) -> Dict[str, Any]:
        """Save yaw PID gains to firmware flash (persists across reboot)."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._yaw_pid_save_pub.publish(msg)
        logger.info(f'Published yaw PID save: kp={kp}, ki={ki}, kd={kd}')
        return {'status': 'ok', 'yaw_pid_saved': {'kp': kp, 'ki': ki, 'kd': kd},
                'note': 'Gains written to firmware flash — will persist after reboot'}

    # -- Buzzer --

    def set_beep(self, duration_ms: int) -> Dict[str, Any]:
        """Control the buzzer: 0=off, 1=continuous, >=10=beep for N ms."""
        msg = UInt16()
        msg.data = int(max(0, duration_ms))
        self._beep_pub.publish(msg)
        if duration_ms == 0:
            description = 'off'
        elif duration_ms == 1:
            description = 'continuous'
        else:
            description = f'{duration_ms}ms'
        logger.info(f'Published beep: {description}')
        return {'status': 'ok', 'buzzer': description}

    # -- Reset / calibration (via services) --

    def reset_odometry(self) -> Dict[str, Any]:
        """Reset firmware odometry to zero."""
        return self.call_service(
            '/orbibot/reset_odometry', 'orbibot_msgs/srv/ResetOdometry', {}, timeout=5.0)

    def reset_encoders(self) -> Dict[str, Any]:
        """Reset encoder counts to zero on MCU."""
        return self.call_service(
            '/orbibot/reset_encoders', 'orbibot_msgs/srv/ResetEncoders', {}, timeout=5.0)

    def calibrate_imu(self, calibration_time: int = 5) -> Dict[str, Any]:
        """Trigger magnetometer auto-calibration."""
        return self.call_service(
            '/orbibot/calibrate_imu', 'orbibot_msgs/srv/CalibrateIMU',
            {'calibration_time': int(calibration_time)},
            timeout=max(calibration_time + 5, 10.0))

    def set_mag_calibration(
        self, offset_x: float, offset_y: float, offset_z: float
    ) -> Dict[str, Any]:
        """Set magnetometer hard-iron calibration offsets (uT)."""
        return self.call_service(
            '/orbibot/set_mag_calibration', 'orbibot_msgs/srv/SetMagCalibration',
            {'offset_x': float(offset_x), 'offset_y': float(offset_y), 'offset_z': float(offset_z)},
            timeout=5.0)

    def reset_firmware_state(self) -> Dict[str, Any]:
        """Emergency: stop motors, reset odometry, clear agent e-stop."""
        self.publish_stop()
        result = self.reset_odometry()
        if self._safety_manager:
            self._safety_manager.reset_emergency_stop()
        logger.warning('Firmware state reset: motors stopped, odometry cleared')
        return {
            'status': 'ok',
            'actions': ['cmd_vel zeroed', 'odometry reset'],
            'note': 'Call set_motor_enable(true) to resume movement',
            'reset_odometry_result': result,
        }

    # -- Firmware version --

    def get_firmware_version(self) -> Optional[Dict[str, Any]]:
        """Get firmware version via /orbibot/get_firmware_version service."""
        try:
            result = self.call_service(
                '/orbibot/get_firmware_version', 'orbibot_msgs/srv/GetFirmwareVersion',
                {}, timeout=3.0)
            if not result.get('success'):
                return {'error': result.get('error', 'Service call failed')}
            resp = result.get('response', {})
            return {
                'version': resp.get('version_string', 'unknown'),
                'major': resp.get('major', 0),
                'minor': resp.get('minor', 0),
            }
        except Exception as e:
            logger.error(f'Failed to get firmware version: {e}')
            return None

    def get_all_firmware_data(self) -> Dict[str, Any]:
        """Get a comprehensive snapshot of all firmware-accessible values."""
        snapshot = {}
        snapshot['battery'] = self.get_battery_status() or {'error': 'unavailable'}
        snapshot['imu_attitude'] = self.get_imu_data() or {'error': 'unavailable'}
        snapshot['imu_raw'] = self.get_imu_raw() or {'error': 'unavailable'}
        snapshot['magnetometer'] = self.get_magnetometer() or {'error': 'unavailable'}
        snapshot['encoders'] = self.get_encoder_counts() or {'error': 'unavailable'}
        snapshot['joint_states'] = self.get_joint_states() or {'error': 'unavailable'}
        snapshot['odometry'] = self.get_odometry() or {'error': 'unavailable'}
        snapshot['safety_status'] = self.get_safety_status() or {'error': 'unavailable'}
        snapshot['firmware_version'] = self.get_firmware_version() or {'error': 'unavailable'}
        snapshot['system'] = self.get_system_enriched() or {'error': 'unavailable'}
        return snapshot
