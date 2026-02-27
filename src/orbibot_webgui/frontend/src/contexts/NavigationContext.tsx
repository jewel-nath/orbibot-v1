/**
 * NavigationContext - Navigation state management for map interactions
 *
 * Manages:
 * - Current interaction mode (init_pose, nav_goal, waypoint)
 * - Waypoint list for patrol routes
 * - Path from /plan topic
 * - Navigation goal status
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from 'react';
import type { ReactNode } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from './RosContext';
import type {
  InteractionMode,
  Waypoint,
  PathPoint,
  GoalStatus,
} from '@/types/interaction';
import { toast } from 'sonner';

// Storage key for persisting waypoints
const WAYPOINTS_STORAGE_KEY = 'orbibot_waypoints';

interface NavigationContextValue {
  // Interaction mode
  mode: InteractionMode;
  setMode: (mode: InteractionMode) => void;

  // Waypoints
  waypoints: Waypoint[];
  addWaypoint: (waypoint: Omit<Waypoint, 'id'>) => void;
  updateWaypoint: (id: string, updates: Partial<Waypoint>) => void;
  removeWaypoint: (id: string) => void;
  reorderWaypoints: (fromIndex: number, toIndex: number) => void;
  clearWaypoints: () => void;
  saveWaypoints: () => void;
  loadWaypoints: () => void;
  exportWaypoints: () => string;
  importWaypoints: (json: string) => boolean;

  // Path display
  path: PathPoint[];

  // Navigation status
  isNavigating: boolean;
  goalStatus: GoalStatus;
  navigationAvailable: boolean;
}

const NavigationContext = createContext<NavigationContextValue | undefined>(
  undefined
);

interface NavigationProviderProps {
  children: ReactNode;
}

export function NavigationProvider({ children }: NavigationProviderProps) {
  const { ros, connectionState } = useRosContext();

  // Interaction mode state
  const [mode, setModeState] = useState<InteractionMode>('none');

  // Waypoints state
  const [waypoints, setWaypoints] = useState<Waypoint[]>(() => {
    // Load from localStorage on init
    try {
      const saved = localStorage.getItem(WAYPOINTS_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Path from /plan topic
  const [path, setPath] = useState<PathPoint[]>([]);

  // Navigation status
  const [isNavigating, setIsNavigating] = useState(false);
  const [goalStatus, setGoalStatus] = useState<GoalStatus>('idle');
  const [navigationAvailable, setNavigationAvailable] = useState(false);

  // Set mode with toast notification
  const setMode = useCallback((newMode: InteractionMode) => {
    setModeState(newMode);

    if (newMode !== 'none') {
      const modeLabels: Record<InteractionMode, string> = {
        none: '',
        init_pose: '2D Pose Estimate',
        nav_goal: 'Navigation Goal',
        waypoint: 'Add Waypoint',
      };

      toast.info(`${modeLabels[newMode]} mode active`, {
        description: 'Click and drag on the map to set pose',
        duration: 2000,
      });
    }
  }, []);

  // Generate unique waypoint ID
  const generateId = () => `wp_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

  // Waypoint management
  const addWaypoint = useCallback((waypoint: Omit<Waypoint, 'id'>) => {
    const newWaypoint: Waypoint = {
      ...waypoint,
      id: generateId(),
    };
    setWaypoints((prev) => [...prev, newWaypoint]);
    toast.success(`Waypoint "${waypoint.name}" added`);
  }, []);

  const updateWaypoint = useCallback((id: string, updates: Partial<Waypoint>) => {
    setWaypoints((prev) =>
      prev.map((wp) => (wp.id === id ? { ...wp, ...updates } : wp))
    );
  }, []);

  const removeWaypoint = useCallback((id: string) => {
    setWaypoints((prev) => {
      const wp = prev.find((w) => w.id === id);
      if (wp) {
        toast.info(`Waypoint "${wp.name}" removed`);
      }
      return prev.filter((w) => w.id !== id);
    });
  }, []);

  const reorderWaypoints = useCallback((fromIndex: number, toIndex: number) => {
    setWaypoints((prev) => {
      const result = [...prev];
      const [removed] = result.splice(fromIndex, 1);
      result.splice(toIndex, 0, removed);
      return result;
    });
  }, []);

  const clearWaypoints = useCallback(() => {
    setWaypoints([]);
    toast.info('All waypoints cleared');
  }, []);

  const saveWaypoints = useCallback(() => {
    try {
      localStorage.setItem(WAYPOINTS_STORAGE_KEY, JSON.stringify(waypoints));
      toast.success('Waypoints saved');
    } catch {
      toast.error('Failed to save waypoints');
    }
  }, [waypoints]);

  const loadWaypoints = useCallback(() => {
    try {
      const saved = localStorage.getItem(WAYPOINTS_STORAGE_KEY);
      if (saved) {
        setWaypoints(JSON.parse(saved));
        toast.success('Waypoints loaded');
      } else {
        toast.info('No saved waypoints found');
      }
    } catch {
      toast.error('Failed to load waypoints');
    }
  }, []);

  const exportWaypoints = useCallback(() => {
    return JSON.stringify({ waypoints }, null, 2);
  }, [waypoints]);

  const importWaypoints = useCallback((json: string): boolean => {
    try {
      const data = JSON.parse(json);
      if (Array.isArray(data.waypoints)) {
        setWaypoints(data.waypoints);
        toast.success(`Imported ${data.waypoints.length} waypoints`);
        return true;
      }
      toast.error('Invalid waypoints format');
      return false;
    } catch {
      toast.error('Failed to parse waypoints JSON');
      return false;
    }
  }, []);

  // Subscribe to /plan topic for path display
  useEffect(() => {
    if (!ros || connectionState !== 'connected') {
      setPath([]);
      return;
    }

    const pathTopic = new ROSLIB.Topic({
      ros,
      name: '/plan',
      messageType: 'nav_msgs/Path',
    });

    const handlePath = (msg: ROSLIB.Message) => {
      const { poses } = msg as unknown as { poses: Array<{ pose: { position: { x: number; y: number } } }> };
      const points: PathPoint[] = poses.map((p) => ({
        x: p.pose.position.x,
        y: p.pose.position.y,
      }));
      setPath(points);
    };

    pathTopic.subscribe(handlePath);
    console.log('[NavigationContext] Subscribed to /plan');

    return () => {
      pathTopic.unsubscribe();
      console.log('[NavigationContext] Unsubscribed from /plan');
    };
  }, [ros, connectionState]);

  // Subscribe to navigation status (navigate_to_pose action feedback)
  useEffect(() => {
    if (!ros || connectionState !== 'connected') {
      setIsNavigating(false);
      setGoalStatus('idle');
      setNavigationAvailable(false);
      return;
    }

    let messageReceived = false;

    // Subscribe to action status topic
    const statusTopic = new ROSLIB.Topic({
      ros,
      name: '/navigate_to_pose/_action/status',
      messageType: 'action_msgs/GoalStatusArray',
    });

    const handleStatus = (msg: ROSLIB.Message) => {
      // Mark navigation as available when we receive first message
      if (!messageReceived) {
        messageReceived = true;
        setNavigationAvailable(true);
      }

      const { status_list } = msg as unknown as { status_list: Array<{ status: number }> };
      if (status_list.length === 0) {
        setIsNavigating(false);
        setGoalStatus('idle');
        return;
      }

      // Get most recent goal status
      const latestStatus = status_list[status_list.length - 1].status;

      // Map ROS action status codes to our GoalStatus
      // STATUS_EXECUTING = 2, STATUS_SUCCEEDED = 4, STATUS_CANCELED = 5, STATUS_ABORTED = 6
      switch (latestStatus) {
        case 1: // ACCEPTED
        case 2: // EXECUTING
          setIsNavigating(true);
          setGoalStatus('navigating');
          break;
        case 4: // SUCCEEDED
          setIsNavigating(false);
          setGoalStatus('succeeded');
          break;
        case 5: // CANCELED
          setIsNavigating(false);
          setGoalStatus('canceled');
          break;
        case 6: // ABORTED
          setIsNavigating(false);
          setGoalStatus('failed');
          break;
        default:
          setIsNavigating(false);
          setGoalStatus('idle');
      }
    };

    // Set a timeout to check if we receive any message
    const availabilityTimeout = setTimeout(() => {
      if (!messageReceived) {
        setNavigationAvailable(false);
      }
    }, 3000); // Wait 3 seconds for first message

    statusTopic.subscribe(handleStatus);
    console.log('[NavigationContext] Subscribed to navigation status');

    return () => {
      statusTopic.unsubscribe();
      clearTimeout(availabilityTimeout);
      console.log('[NavigationContext] Unsubscribed from navigation status');
    };
  }, [ros, connectionState]);

  const value: NavigationContextValue = {
    mode,
    setMode,
    waypoints,
    addWaypoint,
    updateWaypoint,
    removeWaypoint,
    reorderWaypoints,
    clearWaypoints,
    saveWaypoints,
    loadWaypoints,
    exportWaypoints,
    importWaypoints,
    path,
    isNavigating,
    goalStatus,
    navigationAvailable,
  };

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
}

/**
 * Hook to access navigation state
 * Throws error if used outside NavigationProvider
 */
export function useNavigationContext() {
  const context = useContext(NavigationContext);

  if (context === undefined) {
    throw new Error(
      'useNavigationContext must be used within a NavigationProvider'
    );
  }

  return context;
}
