/**
 * useMagnetometer - Subscribe to /imu/mag for magnetometer data.
 */

import { useMemo } from 'react';
import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { MagneticField } from '@/types/ros';

export interface MagData {
  x: number; // µT
  y: number;
  z: number;
}

export function useMagnetometer(): MagData | null {
  const { data } = useSubscriber<MagneticField>({
    topic: ROS_TOPICS.imuMag,
    messageType: ROS_MESSAGE_TYPES.magneticField,
    throttleRate: 100,
  });

  return useMemo(() => {
    if (!data?.magnetic_field) return null;
    return {
      x: data.magnetic_field.x,
      y: data.magnetic_field.y,
      z: data.magnetic_field.z,
    };
  }, [data]);
}
