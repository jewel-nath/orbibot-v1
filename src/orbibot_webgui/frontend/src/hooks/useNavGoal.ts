/**
 * useNavGoal - Hook for sending navigation goals and initial pose to Nav2
 *
 * - sendGoal: publishes to /goal_pose (picked up by bt_navigator)
 * - sendInitialPose: publishes to /initialpose for AMCL
 * - cancelGoal: cancels active navigation via action cancel service
 */

import { useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { toast } from 'sonner';
import { logger } from '@/lib/logger';

const log = logger('useNavGoal');

interface UseNavGoalReturn {
  sendGoal: (x: number, y: number, theta: number) => void;
  sendInitialPose: (x: number, y: number, theta: number) => void;
  cancelGoal: () => void;
  isConnected: boolean;
}

export function useNavGoal(): UseNavGoalReturn {
  const { ros, connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';

  const sendGoal = useCallback(
    (x: number, y: number, theta: number) => {
      if (!ros || !isConnected) {
        toast.error('Not connected to ROS');
        return;
      }

      // Publish to /goal_pose — bt_navigator subscribes and creates NavigateToPose action
      const topic = new ROSLIB.Topic({
        ros,
        name: '/goal_pose',
        messageType: 'geometry_msgs/PoseStamped',
      });

      const qz = Math.sin(theta / 2);
      const qw = Math.cos(theta / 2);

      const message = new ROSLIB.Message({
        header: { frame_id: 'map', stamp: { sec: 0, nanosec: 0 } },
        pose: {
          position: { x, y, z: 0 },
          orientation: { x: 0, y: 0, z: qz, w: qw },
        },
      });

      topic.publish(message);

      log.info(`Nav goal sent: (${x.toFixed(2)}, ${y.toFixed(2)}) @ ${(theta * 180 / Math.PI).toFixed(1)}°`);
      toast.info('Navigation goal sent', {
        description: `Target: (${x.toFixed(2)}, ${y.toFixed(2)}) Heading: ${(theta * 180 / Math.PI).toFixed(1)}°`,
        duration: 3000,
      });
    },
    [ros, isConnected]
  );

  const sendInitialPose = useCallback(
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

      const qz = Math.sin(theta / 2);
      const qw = Math.cos(theta / 2);

      // Covariance: moderate uncertainty for user-placed pose
      const cov = [
        0.25, 0, 0, 0, 0, 0,
        0, 0.25, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0.068,
      ];

      const message = new ROSLIB.Message({
        header: { frame_id: 'map', stamp: { sec: 0, nanosec: 0 } },
        pose: {
          pose: {
            position: { x, y, z: 0 },
            orientation: { x: 0, y: 0, z: qz, w: qw },
          },
          covariance: cov,
        },
      });

      topic.publish(message);

      log.info(`Initial pose set: (${x.toFixed(2)}, ${y.toFixed(2)}) @ ${(theta * 180 / Math.PI).toFixed(1)}°`);
      toast.success('Initial pose set', {
        description: `Position: (${x.toFixed(2)}, ${y.toFixed(2)}) Heading: ${(theta * 180 / Math.PI).toFixed(1)}°`,
        duration: 3000,
      });
    },
    [ros, isConnected]
  );

  const cancelGoal = useCallback(() => {
    if (!ros || !isConnected) {
      toast.error('Not connected to ROS');
      return;
    }

    // Stop motion immediately
    const cmdVelTopic = new ROSLIB.Topic({
      ros,
      name: '/cmd_vel',
      messageType: 'geometry_msgs/Twist',
    });
    cmdVelTopic.publish(new ROSLIB.Message({
      linear: { x: 0, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: 0 },
    }));

    // Cancel navigate_to_pose action (all goals)
    const cancelService = new ROSLIB.Service({
      ros,
      name: '/navigate_to_pose/_action/cancel_goal',
      serviceType: 'action_msgs/CancelGoal',
    });

    cancelService.callService(
      new ROSLIB.ServiceRequest({
        goal_info: {
          goal_id: { uuid: new Array(16).fill(0) },
          stamp: { sec: 0, nanosec: 0 },
        },
      }),
      () => {
        log.info('Navigation canceled');
        toast.warning('Navigation canceled');
      },
      (error: string) => {
        log.warn('Cancel service error:', error);
        toast.warning('Navigation stopped');
      }
    );
  }, [ros, isConnected]);

  return { sendGoal, sendInitialPose, cancelGoal, isConnected };
}