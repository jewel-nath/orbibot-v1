/**
 * useJointStates - Subscribe to /joint_states for per-wheel position and velocity.
 */

import { useMemo } from 'react';
import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES, MOTOR_MAPPING } from '@/lib/constants';
import type { JointState } from '@/types/ros';

export interface WheelState {
  name: string;
  position: string;
  abbreviation: string;
  positionRad: number;
  velocityRadS: number;
}

export function useJointStates(): WheelState[] | null {
  const { data } = useSubscriber<JointState>({
    topic: ROS_TOPICS.jointStates,
    messageType: ROS_MESSAGE_TYPES.jointState,
    throttleRate: 100,
  });

  return useMemo(() => {
    if (!data?.name?.length) return null;

    return MOTOR_MAPPING.map((motor, idx) => {
      // Try to find by joint name pattern (e.g. "front_left_wheel_joint")
      const jointName = `${motor.position}_wheel_joint`;
      let jointIdx = data.name.indexOf(jointName);
      if (jointIdx < 0) jointIdx = idx; // Fallback to positional index

      return {
        name: motor.name,
        position: motor.position,
        abbreviation: motor.abbreviation,
        positionRad: data.position?.[jointIdx] ?? 0,
        velocityRadS: data.velocity?.[jointIdx] ?? 0,
      };
    });
  }, [data]);
}
