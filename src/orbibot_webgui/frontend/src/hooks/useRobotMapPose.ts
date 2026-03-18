/**
 * useRobotMapPose - Robot position in MAP frame
 *
 * When Nav2/AMCL is running, subscribes to /amcl_pose (map frame).
 * Falls back to /odometry/filtered (odom frame) when AMCL is not running.
 *
 * This is the correct source for drawing the robot on the map canvas —
 * /odom and /odometry/filtered are in the odom frame, so they don't
 * reflect AMCL's map→odom correction after Init Pose is set.
 */

import { useState, useEffect, useRef } from 'react';
import { useRos } from '@/contexts/RosContext';
import ROSLIB from 'roslib';

export interface RobotMapPose {
  x: number;
  y: number;
  theta: number; // radians
  source: 'amcl' | 'odom';
}

function quaternionToYaw(q: { x: number; y: number; z: number; w: number }): number {
  const siny = 2 * (q.w * q.z + q.x * q.y);
  const cosy = 1 - 2 * (q.y * q.y + q.z * q.z);
  return Math.atan2(siny, cosy);
}

export function useRobotMapPose(): RobotMapPose | null {
  const { ros, connectionState } = useRos();
  const [pose, setPose] = useState<RobotMapPose | null>(null);
  const amclSubRef = useRef<ROSLIB.Topic | null>(null);
  const odomSubRef = useRef<ROSLIB.Topic | null>(null);
  const amclActiveRef = useRef(false);
  const amclTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!ros || connectionState !== 'connected') {
      setPose(null);
      return;
    }

    // Subscribe to /amcl_pose (map frame — correct source for map overlay)
    const amclSub = new ROSLIB.Topic({
      ros,
      name: '/amcl_pose',
      messageType: 'geometry_msgs/msg/PoseWithCovarianceStamped',
    });

    amclSub.subscribe((msg: any) => {
      amclActiveRef.current = true;

      // Reset timeout: if no amcl_pose for 3s, fall back to odom
      if (amclTimeoutRef.current) clearTimeout(amclTimeoutRef.current);
      amclTimeoutRef.current = setTimeout(() => {
        amclActiveRef.current = false;
      }, 3000);

      const p = msg.pose.pose;
      setPose({
        x: p.position.x,
        y: p.position.y,
        theta: quaternionToYaw(p.orientation),
        source: 'amcl',
      });
    });

    amclSubRef.current = amclSub;

    // Subscribe to /odometry/filtered as fallback (odom frame)
    const odomSub = new ROSLIB.Topic({
      ros,
      name: '/odometry/filtered',
      messageType: 'nav_msgs/msg/Odometry',
    });

    odomSub.subscribe((msg: any) => {
      // Only use odom when AMCL is not providing updates
      if (amclActiveRef.current) return;

      const p = msg.pose.pose;
      setPose({
        x: p.position.x,
        y: p.position.y,
        theta: quaternionToYaw(p.orientation),
        source: 'odom',
      });
    });

    odomSubRef.current = odomSub;

    return () => {
      amclSub.unsubscribe();
      odomSub.unsubscribe();
      if (amclTimeoutRef.current) clearTimeout(amclTimeoutRef.current);
      amclActiveRef.current = false;
    };
  }, [ros, connectionState]);

  return pose;
}
