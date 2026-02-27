/**
 * useWaypointPatrol - Hook for waypoint patrol functionality
 *
 * Manages sequential navigation through a list of waypoints with:
 * - Start/stop patrol controls
 * - Loop mode toggle
 * - Progress tracking
 * - Automatic navigation to next waypoint on arrival
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigationContext } from '@/contexts/NavigationContext';
import { useNavGoal } from '@/hooks/useNavGoal';
import { useOdometry } from '@/hooks/useOdometry';
import { toast } from 'sonner';

interface UseWaypointPatrolOptions {
  arrivalThreshold?: number; // Distance in meters to consider "arrived"
}

interface UseWaypointPatrolReturn {
  isPatrolling: boolean;
  isPaused: boolean;
  currentIndex: number;
  loop: boolean;
  setLoop: (loop: boolean) => void;
  startPatrol: () => void;
  pausePatrol: () => void;
  resumePatrol: () => void;
  stopPatrol: () => void;
  skipToWaypoint: (index: number) => void;
  progress: number; // 0-100 percentage
}

export function useWaypointPatrol(
  options: UseWaypointPatrolOptions = {}
): UseWaypointPatrolReturn {
  const { arrivalThreshold = 0.3 } = options; // 30cm default

  const { waypoints, goalStatus } = useNavigationContext();
  const { sendGoal } = useNavGoal();
  const odom = useOdometry();

  const [isPatrolling, setIsPatrolling] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loop, setLoop] = useState(true);

  // Track if we've sent the goal for current waypoint
  const goalSentRef = useRef(false);
  const lastIndexRef = useRef(-1);

  // Calculate progress percentage
  const progress =
    waypoints.length > 0
      ? Math.round(((currentIndex + (goalStatus === 'succeeded' ? 1 : 0)) / waypoints.length) * 100)
      : 0;

  // Navigate to current waypoint
  const navigateToCurrent = useCallback(() => {
    if (waypoints.length === 0 || currentIndex >= waypoints.length) return;

    const wp = waypoints[currentIndex];
    sendGoal(wp.x, wp.y, wp.theta);
    goalSentRef.current = true;
    lastIndexRef.current = currentIndex;

    toast.info(`Navigating to ${wp.name}`, {
      description: `Waypoint ${currentIndex + 1} of ${waypoints.length}`,
    });
  }, [waypoints, currentIndex, sendGoal]);

  // Start patrol from the beginning
  const startPatrol = useCallback(() => {
    if (waypoints.length === 0) {
      toast.warning('No waypoints to patrol');
      return;
    }

    setCurrentIndex(0);
    setIsPatrolling(true);
    setIsPaused(false);
    goalSentRef.current = false;
    lastIndexRef.current = -1;

    toast.success('Patrol started', {
      description: `${waypoints.length} waypoints to visit`,
    });
  }, [waypoints.length]);

  // Pause patrol (stop navigating but remember position)
  const pausePatrol = useCallback(() => {
    setIsPaused(true);
    toast.info('Patrol paused');
  }, []);

  // Resume patrol from current position
  const resumePatrol = useCallback(() => {
    setIsPaused(false);
    goalSentRef.current = false;
    toast.info('Patrol resumed');
  }, []);

  // Stop patrol completely
  const stopPatrol = useCallback(() => {
    setIsPatrolling(false);
    setIsPaused(false);
    setCurrentIndex(0);
    goalSentRef.current = false;
    lastIndexRef.current = -1;
    toast.info('Patrol stopped');
  }, []);

  // Skip to a specific waypoint
  const skipToWaypoint = useCallback(
    (index: number) => {
      if (index < 0 || index >= waypoints.length) return;

      setCurrentIndex(index);
      goalSentRef.current = false;

      if (isPatrolling && !isPaused) {
        toast.info(`Skipping to ${waypoints[index].name}`);
      }
    },
    [waypoints, isPatrolling, isPaused]
  );

  // Send navigation goal when index changes or patrol starts
  useEffect(() => {
    if (
      isPatrolling &&
      !isPaused &&
      waypoints.length > 0 &&
      !goalSentRef.current &&
      currentIndex < waypoints.length
    ) {
      navigateToCurrent();
    }
  }, [isPatrolling, isPaused, waypoints.length, currentIndex, navigateToCurrent]);

  // Check for waypoint arrival using odometry
  useEffect(() => {
    if (!isPatrolling || isPaused || !odom || waypoints.length === 0) return;

    const target = waypoints[currentIndex];
    if (!target) return;

    const distance = Math.sqrt(
      Math.pow(odom.x - target.x, 2) + Math.pow(odom.y - target.y, 2)
    );

    // Check if we've arrived at the current waypoint
    if (distance < arrivalThreshold && goalSentRef.current) {
      toast.success(`Arrived at ${target.name}`);

      // Move to next waypoint
      const nextIndex = currentIndex + 1;

      if (nextIndex >= waypoints.length) {
        if (loop) {
          // Restart from beginning
          setCurrentIndex(0);
          goalSentRef.current = false;
          toast.info('Patrol loop restarting');
        } else {
          // Patrol complete
          setIsPatrolling(false);
          toast.success('Patrol complete!', {
            description: `Visited all ${waypoints.length} waypoints`,
          });
        }
      } else {
        setCurrentIndex(nextIndex);
        goalSentRef.current = false;
      }
    }
  }, [odom, isPatrolling, isPaused, waypoints, currentIndex, loop, arrivalThreshold]);

  // Also check goal status from Nav2 as backup
  useEffect(() => {
    if (!isPatrolling || isPaused) return;

    if (goalStatus === 'succeeded' && goalSentRef.current && lastIndexRef.current === currentIndex) {
      // Goal reached according to Nav2
      const nextIndex = currentIndex + 1;

      if (nextIndex >= waypoints.length) {
        if (loop) {
          setCurrentIndex(0);
          goalSentRef.current = false;
        } else {
          setIsPatrolling(false);
          toast.success('Patrol complete!');
        }
      } else {
        setCurrentIndex(nextIndex);
        goalSentRef.current = false;
      }
    } else if (goalStatus === 'failed' || goalStatus === 'canceled') {
      // Navigation failed - pause patrol
      setIsPaused(true);
      toast.error('Navigation failed', {
        description: 'Patrol paused. Resume to retry.',
      });
    }
  }, [goalStatus, isPatrolling, isPaused, currentIndex, waypoints.length, loop]);

  // Reset if waypoints change during patrol
  useEffect(() => {
    if (isPatrolling && currentIndex >= waypoints.length) {
      if (waypoints.length === 0) {
        stopPatrol();
      } else {
        setCurrentIndex(0);
        goalSentRef.current = false;
      }
    }
  }, [waypoints.length, isPatrolling, currentIndex, stopPatrol]);

  return {
    isPatrolling,
    isPaused,
    currentIndex,
    loop,
    setLoop,
    startPatrol,
    pausePatrol,
    resumePatrol,
    stopPatrol,
    skipToWaypoint,
    progress,
  };
}
