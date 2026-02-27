/**
 * IMUWidget - Display IMU orientation (roll, pitch, yaw)
 */

import { useIMU } from '@/hooks/useIMU';
import { useRos } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';
import { Compass } from 'lucide-react';

interface IMUWidgetProps {
  className?: string;
  compact?: boolean;
}

export function IMUWidget({ className, compact = false }: IMUWidgetProps) {
  const { isConnected } = useRos();
  const imu = useIMU();

  // Loading/offline state
  if (!isConnected || !imu) {
    return (
      <div className={cn('glass-panel p-3 flex items-center justify-between', className)}>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Compass className="w-4 h-4" />
          <span className="text-sm font-medium">IMU</span>
        </div>
        <span className="text-xs text-muted-foreground">Offline</span>
      </div>
    );
  }

  // Compact mode - single row with orientation
  if (compact) {
    return (
      <div className={cn('glass-panel p-3', className)}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">IMU</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="text-center">
              <span className="text-muted-foreground">Roll </span>
              <span className="font-mono font-semibold">{imu.roll.toFixed(1)}°</span>
            </div>
            <div className="text-center">
              <span className="text-muted-foreground">Pitch </span>
              <span className="font-mono font-semibold">{imu.pitch.toFixed(1)}°</span>
            </div>
            <div className="text-center">
              <span className="text-muted-foreground">Yaw </span>
              <span className="font-mono font-semibold">{imu.yaw.toFixed(1)}°</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Full mode - orientation only
  return (
    <div className={cn('glass-panel p-3', className)}>
      <div className="flex items-center gap-2 mb-3">
        <Compass className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-semibold">IMU</h3>
      </div>

      <div className="text-xs">
        <div className="grid grid-cols-3 gap-2">
          <div className="flex flex-col">
            <span className="text-muted-foreground">Roll</span>
            <span className="font-mono">{imu.roll.toFixed(1)}°</span>
          </div>
          <div className="flex flex-col">
            <span className="text-muted-foreground">Pitch</span>
            <span className="font-mono">{imu.pitch.toFixed(1)}°</span>
          </div>
          <div className="flex flex-col">
            <span className="text-muted-foreground">Yaw</span>
            <span className="font-mono">{imu.yaw.toFixed(1)}°</span>
          </div>
        </div>
      </div>
    </div>
  );
}
