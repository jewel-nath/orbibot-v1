/**
 * useEncoders - Hook for subscribing to encoder data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { EncoderStamped } from '@/types/ros';

/**
 * Hook for subscribing to encoder counts and velocities
 *
 * @returns EncoderStamped with encoder_counts and encoder_velocities arrays or null
 *
 * @example
 * const encoders = useEncoders();
 * encoders?.encoder_counts.forEach((count, i) => {
 *   console.log(`Motor ${i+1}: ${count} counts, ${encoders.encoder_velocities[i]} counts/s`);
 * });
 */
export function useEncoders(): EncoderStamped | null {
  const { data: encoders } = useSubscriber<EncoderStamped>({
    topic: ROS_TOPICS.encoders,
    messageType: ROS_MESSAGE_TYPES.encoderStamped,
  });

  return encoders;
}
