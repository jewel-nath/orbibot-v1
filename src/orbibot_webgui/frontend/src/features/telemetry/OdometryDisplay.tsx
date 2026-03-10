/**
 * OdometryDisplay - Display robot position and velocity from odometry
 */

import { useOdometry } from '@/hooks/useOdometry';
import { useRos } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';
import { MapPin, Info } from 'lucide-react';
import { useState } from 'react';

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
  const odom = useOdometry();
  const [showDetails, setShowDetails] = useState(false);

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

  // Compact mode - single row with position, hover for velocity
  if (compact) {
    return (
      <div
        className={cn('glass-panel p-3 relative', className)}
        onMouseEnter={() => setShowDetails(true)}
        onMouseLeave={() => setShowDetails(false)}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Odometry</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 text-xs">
              <div className="text-center">
                <span className="text-muted-foreground">X </span>
                <span className="font-mono font-semibold">{odom.x.toFixed(2)}m</span>
              </div>
              <div className="text-center">
                <span className="text-muted-foreground">Y </span>
                <span className="font-mono font-semibold">{odom.y.toFixed(2)}m</span>
              </div>
              <div className="text-center">
                <span className="text-muted-foreground">θ </span>
                <span className="font-mono font-semibold">{odom.theta.toFixed(1)}°</span>
              </div>
            </div>
            <Info className="w-3.5 h-3.5 text-muted-foreground" />
          </div>
        </div>

        {/* Hover Tooltip */}
        {showDetails && (
          <div className="absolute left-0 right-0 top-full mt-1 z-[100] p-3 glass-panel shadow-xl">
            <div className="text-xs font-medium mb-2">Velocity</div>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="text-center">
                <div className="text-muted-foreground">Vx</div>
                <div className={cn(
                  'font-mono font-semibold',
                  Math.abs(odom.vx) > 0.01 && 'text-primary'
                )}>
                  {odom.vx.toFixed(2)} m/s
                </div>
              </div>
              <div className="text-center">
                <div className="text-muted-foreground">Vy</div>
                <div className={cn(
                  'font-mono font-semibold',
                  Math.abs(odom.vy) > 0.01 && 'text-primary'
                )}>
                  {odom.vy.toFixed(2)} m/s
                </div>
              </div>
              <div className="text-center">
                <div className="text-muted-foreground">Wz</div>
                <div className={cn(
                  'font-mono font-semibold',
                  Math.abs(odom.vtheta) > 0.01 && 'text-primary'
                )}>
                  {odom.vtheta.toFixed(2)} rad/s
                </div>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t text-xs text-muted-foreground text-center">
              Distance: {Math.sqrt(odom.x ** 2 + odom.y ** 2).toFixed(2)}m
            </div>
          </div>
        )}
      </div>
    );
  }

  // Full mode - dense layout always showing all values
  return (
    <div className={cn('glass-panel p-3', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <MapPin className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-semibold">Odometry</h3>
      </div>

      <div className="space-y-2 text-xs">
        {/* Position */}
        <div className="text-[10px] font-semibold text-muted-foreground uppercase">Position</div>
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

        {/* Velocity */}
        <div className="mt-1 text-[10px] font-semibold text-muted-foreground uppercase">
          Velocity
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div className="flex flex-col">
            <span className="text-muted-foreground">Vx</span>
            <span
              className={cn(
                'font-mono',
                Math.abs(odom.vx) > 0.01 && 'text-primary'
              )}
            >
              {odom.vx.toFixed(2)} m/s
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-muted-foreground">Vy</span>
            <span
              className={cn(
                'font-mono',
                Math.abs(odom.vy) > 0.01 && 'text-primary'
              )}
            >
              {odom.vy.toFixed(2)} m/s
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-muted-foreground">Wz</span>
            <span
              className={cn(
                'font-mono',
                Math.abs(odom.vtheta) > 0.01 && 'text-primary'
              )}
            >
              {odom.vtheta.toFixed(2)} rad/s
            </span>
          </div>
        </div>

        {/* Distance from origin */}
        <div className="flex items-center justify-between pt-1 border-t border-border/40">
          <span className="text-muted-foreground">Distance from origin</span>
          <span className="font-mono">
            {Math.sqrt(odom.x ** 2 + odom.y ** 2).toFixed(2)} m
          </span>
        </div>
      </div>
    </div>
  );
}

