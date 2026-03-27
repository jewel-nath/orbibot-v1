/**
 * useOdometryPath - Accumulate XY position history from raw and filtered odometry.
 *
 * Uses ref-based ring buffers with version counter for efficient rendering.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import { quaternionToYaw } from '@/lib/math';
import type { Odometry } from '@/types/ros';

export interface PathPoint {
  x: number;
  y: number;
  yaw: number;
  t: number;
}

interface UseOdometryPathOptions {
  maxPoints?: number;
  sampleIntervalMs?: number;
}

export function useOdometryPath(options?: UseOdometryPathOptions) {
  const { maxPoints = 2000, sampleIntervalMs = 200 } = options ?? {};

  const rawBufferRef = useRef<PathPoint[]>([]);
  const filteredBufferRef = useRef<PathPoint[]>([]);
  const lastRawSampleRef = useRef(0);
  const lastFilteredSampleRef = useRef(0);
  const [, setVersion] = useState(0);

  const { data: rawOdom } = useSubscriber<Odometry>({
    topic: '/odom',
    messageType: ROS_MESSAGE_TYPES.odometry,
    throttleRate: 100,
  });

  const { data: filteredOdom } = useSubscriber<Odometry>({
    topic: '/odometry/filtered',
    messageType: ROS_MESSAGE_TYPES.odometry,
    throttleRate: 100,
  });

  // Sample raw odom
  useEffect(() => {
    if (!rawOdom) return;
    const now = Date.now();
    if (now - lastRawSampleRef.current < sampleIntervalMs) return;
    lastRawSampleRef.current = now;

    const point: PathPoint = {
      x: rawOdom.pose.pose.position.x,
      y: rawOdom.pose.pose.position.y,
      yaw: quaternionToYaw(rawOdom.pose.pose.orientation),
      t: now,
    };
    rawBufferRef.current.push(point);
    if (rawBufferRef.current.length > maxPoints) {
      rawBufferRef.current = rawBufferRef.current.slice(-maxPoints);
    }
    setVersion(v => v + 1);
  }, [rawOdom, maxPoints, sampleIntervalMs]);

  // Sample filtered odom
  useEffect(() => {
    if (!filteredOdom) return;
    const now = Date.now();
    if (now - lastFilteredSampleRef.current < sampleIntervalMs) return;
    lastFilteredSampleRef.current = now;

    const point: PathPoint = {
      x: filteredOdom.pose.pose.position.x,
      y: filteredOdom.pose.pose.position.y,
      yaw: quaternionToYaw(filteredOdom.pose.pose.orientation),
      t: now,
    };
    filteredBufferRef.current.push(point);
    if (filteredBufferRef.current.length > maxPoints) {
      filteredBufferRef.current = filteredBufferRef.current.slice(-maxPoints);
    }
    setVersion(v => v + 1);
  }, [filteredOdom, maxPoints, sampleIntervalMs]);

  const clear = useCallback(() => {
    rawBufferRef.current = [];
    filteredBufferRef.current = [];
    setVersion(v => v + 1);
  }, []);

  return {
    rawPath: rawBufferRef.current,
    filteredPath: filteredBufferRef.current,
    currentRaw: rawBufferRef.current[rawBufferRef.current.length - 1] ?? null,
    currentFiltered: filteredBufferRef.current[filteredBufferRef.current.length - 1] ?? null,
    clear,
  };
}
