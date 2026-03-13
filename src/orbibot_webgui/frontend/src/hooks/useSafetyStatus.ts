/**
 * useSafetyStatus - Hook for subscribing to /orbibot/safety_status
 */

import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { SafetyStatus } from '@/types/ros';

export function useSafetyStatus(): SafetyStatus | null {
  const { data } = useSubscriber<SafetyStatus>({
    topic: ROS_TOPICS.safetyStatus,
    messageType: ROS_MESSAGE_TYPES.safetyStatus,
  });

  return data;
}
