/**
 * usePublisher - Generic ROS topic publisher hook
 */

import { useEffect, useRef, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { logger } from '@/lib/logger';

const log = logger('usePublisher');

interface UsePublisherOptions {
  topic: string;
  messageType: string;
}

/**
 * Create a ROS topic publisher with automatic lifecycle management
 *
 * @example
 * const publish = usePublisher({
 *   topic: '/cmd_vel',
 *   messageType: 'geometry_msgs/Twist',
 * });
 *
 * publish({ linear: { x: 0.5, y: 0, z: 0 }, angular: { x: 0, y: 0, z: 0 } });
 */
export function usePublisher<T = unknown>(options: UsePublisherOptions) {
  const { topic, messageType } = options;
  const { ros, connectionState } = useRosContext();

  const topicRef = useRef<ROSLIB.Topic | null>(null);

  useEffect(() => {
    // Only create publisher if connected
    if (!ros || connectionState !== 'connected' || !topic) {
      topicRef.current = null;
      return;
    }

    try {
      // Create topic
      const rosTopic = new ROSLIB.Topic({
        ros,
        name: topic,
        messageType,
      });

      topicRef.current = rosTopic;

      log.info(`Publisher created for ${topic} (${messageType})`);
    } catch (err) {
      log.error(`Failed to create publisher for ${topic}:`, err);
      topicRef.current = null;
    }

    // Cleanup on unmount
    return () => {
      if (topicRef.current) {
        topicRef.current.unadvertise();
        topicRef.current = null;
        log.info(`Publisher closed for ${topic}`);
      }
    };
  }, [ros, connectionState, topic, messageType]);

  const publish = useCallback(
    (message: T) => {
      if (!topicRef.current) {
        log.warn(`Cannot publish to ${topic}: not connected`);
        return;
      }

      try {
        const rosMessage = new ROSLIB.Message(message as Record<string, unknown>);
        topicRef.current.publish(rosMessage);
      } catch (err) {
        log.error(`Failed to publish to ${topic}:`, err);
      }
    },
    [topic]
  );

  return publish;
}