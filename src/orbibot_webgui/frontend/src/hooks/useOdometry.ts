/**
 * useOdometry - Hook for subscribing to odometry data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Odometry, OdometryData } from '@/types/ros';

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
 * Hook for subscribing to odometry data
 *
 * @returns OdometryData with position (x, y, theta) and velocity (vx, vy, vtheta) or null
 *
 * @example
 * const odom = useOdometry();
 * console.log(`Position: (${odom.x.toFixed(2)}, ${odom.y.toFixed(2)}) at ${odom.theta.toFixed(1)}°`);
 */
import { useSettings } from '@/contexts/SettingsContext';

// ...

export function useOdometry(): OdometryData | null {
  const { settings } = useSettings();
  const { data: odom } = useSubscriber<Odometry>({
    topic: settings.odomTopic,
    messageType: ROS_MESSAGE_TYPES.odometry,
  });

  if (!odom) {
    return null;
  }

  // Extract position
  const x = odom.pose.pose.position.x;
  const y = odom.pose.pose.position.y;

  // Convert quaternion to yaw angle
  const euler = quaternionToEuler(odom.pose.pose.orientation);
  const theta = euler.yaw; // degrees

  // Extract velocities
  const vx = odom.twist.twist.linear.x;
  const vy = odom.twist.twist.linear.y;
  const vtheta = odom.twist.twist.angular.z; // rad/s

  return {
    x,
    y,
    theta,
    vx,
    vy,
    vtheta,
  };
}
