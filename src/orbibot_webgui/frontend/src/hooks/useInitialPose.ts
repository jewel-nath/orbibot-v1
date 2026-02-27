/**
 * useInitialPose - Hook for publishing 2D Pose Estimate
 *
 * Publishes to /initialpose topic (geometry_msgs/PoseWithCovarianceStamped)
 * Used to set the robot's initial position in the map for AMCL localization.
 */

import { useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { toast } from 'sonner';
import { logger } from '@/lib/logger';

const log = logger('useInitialPose');

// Default covariance for initial pose (6x6 matrix, row-major)
// Diagonal elements represent variance in x, y, z, roll, pitch, yaw
const DEFAULT_COVARIANCE = [
  0.25, 0, 0, 0, 0, 0,
  0, 0.25, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0.0685  // ~4 degrees variance for yaw
];

interface UseInitialPoseReturn {
  publishInitialPose: (x: number, y: number, theta: number) => void;
  isConnected: boolean;
}

export function useInitialPose(): UseInitialPoseReturn {
  const { ros, connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';

  const publishInitialPose = useCallback(
    (x: number, y: number, theta: number) => {
      if (!ros || !isConnected) {
        toast.error('Not connected to ROS');
        return;
      }

      const topic = new ROSLIB.Topic({
        ros,
        name: '/initialpose',
        messageType: 'geometry_msgs/PoseWithCovarianceStamped',
      });

      // Convert theta (yaw) to quaternion
      // For 2D rotation around Z-axis: qz = sin(theta/2), qw = cos(theta/2)
      const qz = Math.sin(theta / 2);
      const qw = Math.cos(theta / 2);

      const message = new ROSLIB.Message({
        header: {
          frame_id: 'map',
          stamp: {
            sec: 0,
            nanosec: 0,
          },
        },
        pose: {
          pose: {
            position: {
              x,
              y,
              z: 0,
            },
            orientation: {
              x: 0,
              y: 0,
              z: qz,
              w: qw,
            },
          },
          covariance: DEFAULT_COVARIANCE,
        },
      });

      topic.publish(message);

      log.info(
        `Published initial pose: x=${x.toFixed(2)}, y=${y.toFixed(2)}, theta=${(theta * 180 / Math.PI).toFixed(1)}°`
      );

      toast.success('Initial pose set', {
        description: `Position: (${x.toFixed(2)}, ${y.toFixed(2)}) Heading: ${(theta * 180 / Math.PI).toFixed(1)}°`,
        duration: 3000,
      });
    },
    [ros, isConnected]
  );

  return {
    publishInitialPose,
    isConnected,
  };
}