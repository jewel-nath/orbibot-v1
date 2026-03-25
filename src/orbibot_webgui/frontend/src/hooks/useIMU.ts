/**
 * useIMU - Hook for subscribing to IMU data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import { quaternionToEuler } from '@/lib/math';
import type { Imu, IMUData } from '@/types/ros';
import { useSettings } from '@/contexts/SettingsContext';

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

  const euler = quaternionToEuler(imu.orientation);

  return {
    roll: euler.roll,
    pitch: euler.pitch,
    yaw: euler.yaw,
    angular_velocity: imu.angular_velocity,
    linear_acceleration: imu.linear_acceleration,
  };
}
