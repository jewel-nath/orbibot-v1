/**
 * useMotors - Hook for subscribing to motor states from system status
 */

import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES, MOTOR_MAPPING } from '@/lib/constants';
import type { SystemStatus, MotorState, EncoderStamped } from '@/types/ros';

/**
 * Hook for subscribing to motor states (enabled, current, temperature)
 * Combined with encoder data for complete motor status
 *
 * @returns Array of 4 MotorState objects [M1, M2, M3, M4] or null if not available
 *
 * @example
 * const motors = useMotors();
 * motors?.forEach(motor => {
 *   console.log(`${motor.name} (${motor.position}): ${motor.enabled ? 'ON' : 'OFF'}`);
 * });
 */
export function useMotors(): MotorState[] | null {
  const { data: systemStatus } = useSubscriber<SystemStatus>({
    topic: ROS_TOPICS.systemStatus,
    messageType: ROS_MESSAGE_TYPES.systemStatus,
  });

  const { data: encoderData } = useSubscriber<EncoderStamped>({
    topic: ROS_TOPICS.encoders,
    messageType: ROS_MESSAGE_TYPES.encoderStamped,
  });

  if (!systemStatus) {
    return null;
  }

  // Build motor state array from available data
  // SystemStatus only has a single motors_enabled bool (not per-motor)
  // Encoder topic is std_msgs/Int32MultiArray with data: [M1, M2, M3, M4]
  const motors: MotorState[] = MOTOR_MAPPING.map((motor, index) => ({
    id: motor.id,
    name: motor.name,
    position: motor.position,
    abbreviation: motor.abbreviation,
    enabled: systemStatus.motors_enabled ?? false,
    current: 0,
    temperature: 0,
    encoderCount: encoderData?.data?.[index] ?? 0,
    encoderVelocity: 0,
  }));

  return motors;
}
