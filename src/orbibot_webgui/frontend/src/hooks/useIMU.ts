/**
 * useIMU - Hook for subscribing to IMU data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Imu, IMUData } from '@/types/ros';
import { useSettings } from '@/contexts/SettingsContext';

/**
 * Convert quaternion to Euler angles
 * @param q Quaternion
 * @returns Euler angles in degrees {roll, pitch, yaw}
 */
function quaternionToEuler(q: { x: number; y: number; z: number; w: number }) {
  // Roll (x-axis rotation)
  const sinr_cosp = 2 * (q.w * q.x + q.y * q.z);
  const cosr_cosp = 1 - 2 * (q.x * q.x + q.y * q.y);
  const roll = Math.atan2(sinr_cosp, cosr_cosp);

  // Pitch (y-axis rotation)
  const sinp = 2 * (q.w * q.y - q.z * q.x);
  const pitch = Math.abs(sinp) >= 1
    ? Math.sign(sinp) * Math.PI / 2 // Use 90 degrees if out of range
    : Math.asin(sinp);

  // Yaw (z-axis rotation)
  const siny_cosp = 2 * (q.w * q.z + q.x * q.y);
  const cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z);
  const yaw = Math.atan2(siny_cosp, cosy_cosp);

  // Convert to degrees
  return {
    roll: roll * (180 / Math.PI),
    pitch: pitch * (180 / Math.PI),
    yaw: yaw * (180 / Math.PI),
  };
}

/**
 * Hook for subscribing to IMU data
 *
 * @returns IMUData with orientation (roll, pitch, yaw) and angular velocity or null
 *
 * @example
 * const imu = useIMU();
 * console.log(`Orientation: R=${imu.roll.toFixed(1)}° P=${imu.pitch.toFixed(1)}° Y=${imu.yaw.toFixed(1)}°`);
 */
export function useIMU(): IMUData | null {
  const { settings } = useSettings();
  const { data: imu } = useSubscriber<Imu>({
    topic: settings.imuTopic,
    messageType: ROS_MESSAGE_TYPES.imu,
  });

  if (!imu) {
    return null;
  }

  // Convert quaternion to Euler angles
  const euler = quaternionToEuler(imu.orientation);

  return {
    roll: euler.roll,
    pitch: euler.pitch,
    yaw: euler.yaw,
    angular_velocity: imu.angular_velocity,
  };
}
