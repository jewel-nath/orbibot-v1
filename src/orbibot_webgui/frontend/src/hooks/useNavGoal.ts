/**
 * useNavGoal - Hook for sending navigation goals to Nav2
 *
 * Publishes to /goal_pose topic (geometry_msgs/PoseStamped)
 * and can cancel navigation via action cancel.
 */

import { useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { toast } from 'sonner';
import { logger } from '@/lib/logger';

const log = logger('useNavGoal');

interface UseNavGoalReturn {
  sendGoal: (x: number, y: number, theta: number) => void;
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

      const topic = new ROSLIB.Topic({
        ros,
        name: '/goal_pose',
        messageType: 'geometry_msgs/PoseStamped',
      });

      // Convert theta (yaw) to quaternion
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
      });

      topic.publish(message);

      log.info(
        `Sent navigation goal: x=${x.toFixed(2)}, y=${y.toFixed(2)}, theta=${(theta * 180 / Math.PI).toFixed(1)}°`
      );

      toast.info('Navigation goal sent', {
        description: `Target: (${x.toFixed(2)}, ${y.toFixed(2)}) Heading: ${(theta * 180 / Math.PI).toFixed(1)}°`,
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

    // Method 1: Publish empty goal to stop navigation
    const cmdVelTopic = new ROSLIB.Topic({
      ros,
      name: '/cmd_vel',
      messageType: 'geometry_msgs/Twist',
    });

    const stopMessage = new ROSLIB.Message({
      linear: { x: 0, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: 0 },
    });

    cmdVelTopic.publish(stopMessage);

    // Method 2: Call the cancel service for navigate_to_pose action
    const cancelService = new ROSLIB.Service({
      ros,
      name: '/navigate_to_pose/_action/cancel_goal',
      serviceType: 'action_msgs/CancelGoal',
    });

    const cancelRequest = new ROSLIB.ServiceRequest({
      goal_info: {
        goal_id: {
          uuid: new Array(16).fill(0), // Cancel all goals
        },
        stamp: {
          sec: 0,
          nanosec: 0,
        },
      },
    });

    cancelService.callService(
      cancelRequest,
      () => {
        log.info('Navigation canceled');
        toast.warning('Navigation canceled');
      },
      (error: string) => {
        log.warn('Cancel service error:', error);
        // Still show success since we stopped cmd_vel
        toast.warning('Navigation stopped');
      }
    );
  }, [ros, isConnected]);

  return {
    sendGoal,
    cancelGoal,
    isConnected,
  };
}