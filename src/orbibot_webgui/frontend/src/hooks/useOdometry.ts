/**
 * useOdometry - Hook for subscribing to odometry data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import { quaternionToEuler } from '@/lib/math';
import type { Odometry, OdometryData } from '@/types/ros';
import { useSettings } from '@/contexts/SettingsContext';

/**
 * Hook for subscribing to odometry data
 *
 * @returns OdometryData with position (x, y, theta) and velocity (vx, vy, vtheta) or null
 *
 * @example
 * const odom = useOdometry();
 * console.log(`Position: (${odom.x.toFixed(2)}, ${odom.y.toFixed(2)}) at ${odom.theta.toFixed(1)}°`);
 */
export function useOdometry(): OdometryData | null {
  const { settings } = useSettings();
  const { data: odom } = useSubscriber<Odometry>({
    topic: settings.odomTopic,
    messageType: ROS_MESSAGE_TYPES.odometry,
  });

  if (!odom) {
    return null;
  }

  const x = odom.pose.pose.position.x;
  const y = odom.pose.pose.position.y;
  const euler = quaternionToEuler(odom.pose.pose.orientation);
  const theta = euler.yaw; // degrees

  const vx = odom.twist.twist.linear.x;
  const vy = odom.twist.twist.linear.y;
  const vtheta = odom.twist.twist.angular.z; // rad/s

  return { x, y, theta, vx, vy, vtheta };
}
