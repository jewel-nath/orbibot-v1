/**
 * useOdomSampling - Record /odom velocity samples while recording (for PID response graph).
 * When isRecording is true, subscribes to odom topic and appends { t, vx, vy, wz } to samples.
 * t is seconds since recording started.
 */

import { useEffect, useRef, useState } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { useSettings } from '@/contexts/SettingsContext';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Odometry } from '@/types/ros';

export interface OdomSample {
  t: number;
  vx: number;
  vy: number;
  wz: number;
}

export function useOdomSampling(isRecording: boolean) {
  const { ros, connectionState } = useRosContext();
  const { settings } = useSettings();
  const [samples, setSamples] = useState<OdomSample[]>([]);
  const t0Ref = useRef<number>(0);
  const topicRef = useRef<ROSLIB.Topic | null>(null);

  // When recording starts, reset time origin and clear samples
  useEffect(() => {
    if (isRecording) {
      t0Ref.current = Date.now();
      setSamples([]);
    }
  }, [isRecording]);

  // Subscribe to /odom while recording and append samples
  useEffect(() => {
    if (!isRecording || !ros || connectionState !== 'connected' || !settings.odomTopic) {
      if (topicRef.current) {
        topicRef.current.unsubscribe();
        topicRef.current = null;
      }
      return;
    }

    const topic = new ROSLIB.Topic({
      ros,
      name: settings.odomTopic,
      messageType: ROS_MESSAGE_TYPES.odometry,
    });

    const handler = (message: ROSLIB.Message) => {
      const odom = message as unknown as Odometry;
      const t = (Date.now() - t0Ref.current) / 1000;
      const vx = odom.twist.twist.linear.x;
      const vy = odom.twist.twist.linear.y;
      const wz = odom.twist.twist.angular.z;
      setSamples((prev) => [...prev, { t, vx, vy, wz }]);
    };

    topic.subscribe(handler);
    topicRef.current = topic;

    return () => {
      topic.unsubscribe();
      topicRef.current = null;
    };
  }, [isRecording, ros, connectionState, settings.odomTopic]);

  const clearSamples = () => setSamples([]);

  return { samples, clearSamples };
}
