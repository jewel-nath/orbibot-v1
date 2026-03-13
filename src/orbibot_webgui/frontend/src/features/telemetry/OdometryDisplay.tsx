/**
 * OdometryDisplay - Display robot position and velocity from odometry
 */

import { useOdometry } from '@/hooks/useOdometry';
import { useRos } from '@/contexts/RosContext';
import { useSettings } from '@/contexts/SettingsContext';
import { cn } from '@/lib/utils';
import { MapPin } from 'lucide-react';

function odomSourceLabel(topic: string): string {
  if (topic === '/odometry/filtered') return 'Fused';
  return 'Wheel';
}

interface OdometryDisplayProps {
  className?: string;
  compact?: boolean;
}

/**
 * OdometryDisplay component
 * Shows robot position (x, y, theta) and velocity (vx, vy, vtheta) from wheel odometry
 */
export function OdometryDisplay({ className, compact = false }: OdometryDisplayProps) {
  const { isConnected } = useRos();
  const { settings } = useSettings();
  const odom = useOdometry();
  const sourceLabel = odomSourceLabel(settings.odomTopic);
  const sourceTitle = settings.odomTopic === '/odometry/filtered'
    ? 'EKF-fused odometry (localization running)'
    : 'Wheel odometry from /odom';

  // Loading / offline / waiting state
  if (!isConnected || !odom) {
    const statusText = !isConnected ? 'Offline' : 'Waiting for data…';
    return (
      <div className={cn('glass-panel p-3 flex items-center justify-between', className)}>
        <div className="flex items-center gap-2 text-muted-foreground">
          <MapPin className="w-4 h-4" />
          <span className="text-sm font-medium">Odometry</span>
        </div>
        <span className="text-xs text-muted-foreground">{statusText}</span>
      </div>
    );
  }

  // Compact mode - same structure as IMUWidget: one header row, one border-t row
  if (compact) {
    return (
      <div className={cn('glass-panel p-3', className)}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Odometry</span>
            <span className="text-[10px] font-medium text-muted-foreground" title={sourceTitle}>
              ({sourceLabel})
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="text-center">
              <span className="text-muted-foreground">X </span>
              <span className="font-mono font-semibold">{odom.x.toFixed(2)} m</span>
            </div>
            <div className="text-center">
              <span className="text-muted-foreground">Y </span>
              <span className="font-mono font-semibold">{odom.y.toFixed(2)} m</span>
            </div>
            <div className="text-center">
              <span className="text-muted-foreground">θ </span>
              <span className="font-mono font-semibold">{odom.theta.toFixed(1)}°</span>
            </div>
          </div>
        </div>
        <div className="mt-2 pt-2 border-t border-border/40 flex justify-between text-[10px]">
          <span className="text-muted-foreground">Distance</span>
          <span className="font-mono">{Math.sqrt(odom.x ** 2 + odom.y ** 2).toFixed(2)} m</span>
        </div>
      </div>
    );
  }

  // Full mode - IMUWidget-style sections with same spacing and typography
  return (
    <div className={cn('glass-panel p-3', className)}>
      <div className="flex items-center gap-2 mb-3">
        <MapPin className="w-4 h-4 text-primary" />
        <span className="text-sm font-semibold">Odometry</span>
        <span className="text-[10px] font-medium text-muted-foreground" title={sourceTitle}>
          ({sourceLabel})
        </span>
      </div>

      <div className="text-xs space-y-3">
        <div>
          <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">Position</div>
          <div className="grid grid-cols-3 gap-2">
            <div className="flex flex-col">
              <span className="text-muted-foreground">X</span>
              <span className="font-mono">{odom.x.toFixed(2)} m</span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground">Y</span>
              <span className="font-mono">{odom.y.toFixed(2)} m</span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground">θ</span>
              <span className="font-mono">{odom.theta.toFixed(1)}°</span>
            </div>
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">Velocity</div>
          <div className="grid grid-cols-3 gap-2">
            <div className="flex flex-col">
              <span className="text-muted-foreground">Vx</span>
              <span className={cn('font-mono', Math.abs(odom.vx) > 0.01 && 'text-primary')}>
                {odom.vx.toFixed(2)} m/s
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground">Vy</span>
              <span className={cn('font-mono', Math.abs(odom.vy) > 0.01 && 'text-primary')}>
                {odom.vy.toFixed(2)} m/s
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-muted-foreground">Wz</span>
              <span className={cn('font-mono', Math.abs(odom.vtheta) > 0.01 && 'text-primary')}>
                {odom.vtheta.toFixed(2)} rad/s
              </span>
            </div>
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">Distance from origin</div>
          <div className="font-mono">{Math.sqrt(odom.x ** 2 + odom.y ** 2).toFixed(2)} m</div>
        </div>
      </div>
    </div>
  );
}

