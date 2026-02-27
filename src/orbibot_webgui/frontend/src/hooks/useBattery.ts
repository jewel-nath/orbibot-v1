/**
 * useBattery - Hook for subscribing to battery status from system status topic
 */

import { useSubscriber } from './useSubscriber';
import { ROS_TOPICS, ROS_MESSAGE_TYPES, BATTERY_PARAMS } from '@/lib/constants';
import type { SystemStatus, BatteryStatus } from '@/types/ros';

/**
 * Hook for subscribing to battery voltage and status
 *
 * @returns BatteryStatus with voltage, percentage, and status level
 *
 * @example
 * const battery = useBattery();
 * console.log(`Battery: ${battery.voltage}V (${battery.percentage}%) - ${battery.status}`);
 */
export function useBattery(): BatteryStatus | null {
  const { data: systemStatus } = useSubscriber<SystemStatus>({
    topic: ROS_TOPICS.systemStatus,
    messageType: ROS_MESSAGE_TYPES.systemStatus,
  });

  if (!systemStatus) {
    return null;
  }

  const voltage = systemStatus.battery_voltage;
  // Calculate percentage from voltage (4S LiFePO4: 10.5V empty → 14.6V full)
  const range = BATTERY_PARAMS.full - BATTERY_PARAMS.criticalThreshold;
  const percentage = Math.min(100, Math.max(0,
    ((voltage - BATTERY_PARAMS.criticalThreshold) / range) * 100
  ));

  // Determine battery status based on 4S LiFePO4 thresholds
  let status: BatteryStatus['status'];
  if (voltage >= BATTERY_PARAMS.full) {
    status = 'full';
  } else if (voltage >= BATTERY_PARAMS.lowThreshold) {
    status = 'normal';
  } else if (voltage >= BATTERY_PARAMS.criticalThreshold) {
    status = 'low';
  } else {
    status = 'critical';
  }

  return {
    voltage,
    percentage,
    status,
  };
}
