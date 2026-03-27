/**
 * useRawIMU - Subscribe to /imu/data_raw for unfiltered IMU data.
 */

import { useMemo } from 'react';
import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Imu, Vector3 } from '@/types/ros';

export interface RawIMUData {
  gyro: Vector3;   // rad/s
  accel: Vector3;  // m/s²
}

export function useRawIMU(): RawIMUData | null {
  const { data } = useSubscriber<Imu>({
    topic: ROS_TOPICS.imuRaw,
    messageType: ROS_MESSAGE_TYPES.imu,
    throttleRate: 50,
  });

  return useMemo(() => {
    if (!data) return null;
    return {
      gyro: data.angular_velocity ?? { x: 0, y: 0, z: 0 },
      accel: data.linear_acceleration ?? { x: 0, y: 0, z: 0 },
    };
  }, [data]);
}
