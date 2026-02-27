/**
 * useMap - Subscribe to SLAM map data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';

export interface MapMetaData {
  map_load_time: {
    sec: number;
    nanosec: number;
  };
  resolution: number;  // meters/pixel
  width: number;       // Map width in pixels
  height: number;      // Map height in pixels
  origin: {
    position: {
      x: number;       // meters
      y: number;       // meters
      z: number;       // meters
    };
    orientation: {
      x: number;
      y: number;
      z: number;
      w: number;
    };
  };
}

export interface OccupancyGrid {
  header: {
    stamp: {
      sec: number;
      nanosec: number;
    };
    frame_id: string;
  };
  info: MapMetaData;
  data: number[];      // Occupancy data: -1 = unknown, 0 = free, 100 = occupied
}

/**
 * Hook to subscribe to SLAM map data
 * @returns OccupancyGrid data or null if not available
 */
import { useSettings } from '@/contexts/SettingsContext';

// ...

export function useMap(): OccupancyGrid | null {
  const { settings } = useSettings();
  const { data: map } = useSubscriber<OccupancyGrid>({
    topic: settings.mapTopic,
    messageType: ROS_MESSAGE_TYPES.occupancyGrid,
  });

  return map;
}
