/**
 * useCmdVel - Specific hook for publishing velocity commands
 */

import { useCallback } from 'react';
import { usePublisher } from './usePublisher';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Twist } from '@/types/ros';

interface VelocityCommand {
  vx: number;  // m/s (forward/backward)
  vy: number;  // m/s (strafe left/right)
  wz: number;  // rad/s (rotation)
}

/**
 * Hook for publishing velocity commands to /cmd_vel
 *
 * @example
 * const { publishVelocity, stop } = useCmdVel();
 *
 * // Move forward
 * publishVelocity({ vx: 0.5, vy: 0, wz: 0 });
 *
 * // Stop
 * stop();
 */
export function useCmdVel() {
  const publish = usePublisher<Twist>({
    topic: ROS_TOPICS.cmdVel,
    messageType: ROS_MESSAGE_TYPES.twist,
  });

  const publishVelocity = useCallback(
    ({ vx, vy, wz }: VelocityCommand) => {
      const twist: Twist = {
        linear: { x: vx, y: vy, z: 0 },
        angular: { x: 0, y: 0, z: wz },
      };

      publish(twist);
    },
    [publish]
  );

  const stop = useCallback(() => {
    publishVelocity({ vx: 0, vy: 0, wz: 0 });
  }, [publishVelocity]);

  return { publishVelocity, stop };
}
