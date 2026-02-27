/**
 * useLidarScan - Subscribe to LiDAR scan data
 */

import { useSubscriber } from './useSubscriber';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';

export interface LaserScan {
  header: {
    stamp: {
      sec: number;
      nanosec: number;
    };
    frame_id: string;
  };
  angle_min: number;        // Start angle of scan (radians)
  angle_max: number;        // End angle of scan (radians)
  angle_increment: number;  // Angular distance between measurements (radians)
  time_increment: number;   // Time between measurements (seconds)
  scan_time: number;        // Time between scans (seconds)
  range_min: number;        // Minimum range value (meters)
  range_max: number;        // Maximum range value (meters)
  ranges: number[];         // Range data (meters) - Inf indicates no return
  intensities: number[];    // Intensity data (device specific units)
}

/**
 * Hook to subscribe to LiDAR scan data
 * @returns LaserScan data or null if not available
 */
import { useSettings } from '@/contexts/SettingsContext';

// ...

export function useLidarScan(): LaserScan | null {
  const { settings } = useSettings();
  const { data: scan } = useSubscriber<LaserScan>({
    topic: settings.scanTopic,
    messageType: ROS_MESSAGE_TYPES.laserScan,
  });

  return scan;
}
