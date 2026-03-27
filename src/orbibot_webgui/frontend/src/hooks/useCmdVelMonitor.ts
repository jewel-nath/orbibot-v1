/**
 * useCmdVelMonitor - Read-only subscribe to /cmd_vel to track commanded velocity.
 */

import { useMemo } from 'react';
import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Twist } from '@/types/ros';

export interface CmdVelState {
  vx: number;
  vy: number;
  wz: number;
}

export function useCmdVelMonitor(): CmdVelState | null {
  const { data } = useSubscriber<Twist>({
    topic: ROS_TOPICS.cmdVel,
    messageType: ROS_MESSAGE_TYPES.twist,
    throttleRate: 100,
  });

  return useMemo(() => {
    if (!data) return null;
    return {
      vx: data.linear?.x ?? 0,
      vy: data.linear?.y ?? 0,
      wz: data.angular?.z ?? 0,
    };
  }, [data]);
}
