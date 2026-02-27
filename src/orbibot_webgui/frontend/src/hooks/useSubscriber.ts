/**
 * useSubscriber - Generic ROS topic subscription hook
 *
 * Pattern adapted from reference dashboard but simplified for single-robot use
 */

import { useEffect, useRef, useState } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { logger } from '@/lib/logger';

const log = logger('useSubscriber');

interface UseSubscriberOptions {
  topic: string;
  messageType: string;
  throttleRate?: number; // ms between messages
  enabled?: boolean;     // Allow conditional subscription
}

interface UseSubscriberReturn<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Subscribe to a ROS topic with automatic lifecycle management
 *
 * @example
 * const { data: odom, loading, error } = useSubscriber<Odometry>({
 *   topic: '/odom',
 *   messageType: 'nav_msgs/Odometry',
 * });
 */
export function useSubscriber<T = unknown>(
  options: UseSubscriberOptions
): UseSubscriberReturn<T> {
  const { topic, messageType, throttleRate, enabled = true } = options;
  const { ros, connectionState } = useRosContext();

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const topicRef = useRef<ROSLIB.Topic | null>(null);
  const isSubscribedRef = useRef(false);

  useEffect(() => {
    // Only subscribe if enabled and connected
    if (!enabled || !ros || connectionState !== 'connected' || !topic) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Create topic
      const rosTopic = new ROSLIB.Topic({
        ros,
        name: topic,
        messageType,
        throttle_rate: throttleRate,
      });

      // Subscribe to topic
      rosTopic.subscribe((message) => {
        setData(message as T);
        setLoading(false);
      });

      topicRef.current = rosTopic;
      isSubscribedRef.current = true;

      log.info(`Subscribed to ${topic} (${messageType})`);
    } catch (err) {
      log.error(`Failed to subscribe to ${topic}:`, err);
      setError(err as Error);
      setLoading(false);
    }

    // Cleanup on unmount or when dependencies change
    return () => {
      if (topicRef.current && isSubscribedRef.current) {
        topicRef.current.unsubscribe();
        isSubscribedRef.current = false;
        log.info(`Unsubscribed from ${topic}`);
      }
      topicRef.current = null;
    };
  }, [ros, connectionState, topic, messageType, throttleRate, enabled]);

  return { data, loading, error };
}