/**
 * ObstacleIndicator - Visual indicator for LiDAR-based obstacle detection
 *
 * Features:
 * - Real-time obstacle status from /orbibot/obstacle_detected topic
 * - Emergency stop status from /orbibot/emergency_stop topic
 * - Visual states: Clear (green), Warning (yellow), Emergency (red)
 * - Compact, badge, or full panel display modes
 */

import { Shield, AlertTriangle, XOctagon, Check, Bot } from 'lucide-react';
import { useRosContext } from '@/contexts/RosContext';
import { useSubscriber } from '@/hooks/useSubscriber';
import { cn } from '@/lib/utils';

type SafetyStatus = 'clear' | 'warning' | 'emergency' | 'unknown';

// 8-sector layout mapped to a 3x3 grid (center = robot)
// Sector indices from obstacle_detector: F(0) FL(1) L(2) BL(3) B(4) BR(5) R(6) FR(7)
const SECTOR_GRID: [number, string][] = [
  [1, 'FL'], [0, 'F'],  [7, 'FR'],
  [2, 'L'],  [-1, ''],  [6, 'R'],
  [3, 'BL'], [4, 'B'],  [5, 'BR'],
];

function getSectorColor(dist: number) {
  if (!isFinite(dist) || dist > 10) return 'bg-muted/20 text-muted-foreground border-border/20';
  if (dist < 0.25) return 'bg-red-500/25 text-red-400 border-red-500/40';
  if (dist < 0.5) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
  return 'bg-primary/15 text-primary border-primary/25';
}

function SectorRadar({ sectors }: { sectors: number[] }) {
  // Defensive check for invalid data
  if (!sectors || !Array.isArray(sectors) || sectors.length !== 8) {
    return (
      <div className="text-xs text-muted-foreground text-center py-4">
        Waiting for sector data...
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-1">
      {SECTOR_GRID.map(([idx, label], i) => {
        if (idx === -1) {
          return (
            <div key={i} className="flex items-center justify-center rounded-md border border-border/30 bg-card/50 py-2">
              <Bot className="w-3.5 h-3.5 text-primary" />
            </div>
          );
        }
        const dist = sectors[idx] ?? Infinity;
        const isInf = !isFinite(dist) || dist > 10;
        return (
          <div key={i} className={cn(
            'flex flex-col items-center justify-center rounded-md border py-1.5',
            getSectorColor(dist)
          )}>
            <span className="text-[9px] font-bold leading-none">{label}</span>
            <span className="text-[10px] font-mono leading-tight mt-0.5">
              {isInf ? '—' : `${dist.toFixed(1)}m`}
            </span>
          </div>
        );
      })}
    </div>
  );
}

interface ObstacleIndicatorProps {
  className?: string;
  variant?: 'badge' | 'panel';
  compact?: boolean;
}

export function ObstacleIndicator({
  className,
  variant = 'panel',
  compact = false,
}: ObstacleIndicatorProps) {
  const { connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';

  // Subscribe to obstacle detection topics using shared hook pattern
  const { data: obstacleMsg } = useSubscriber<{ data: boolean }>({
    topic: '/orbibot/obstacle_detected',
    messageType: 'std_msgs/Bool',
  });

  const { data: emergencyMsg } = useSubscriber<{ data: boolean }>({
    topic: '/orbibot/emergency_stop',
    messageType: 'std_msgs/Bool',
  });

  const { data: distanceMsg } = useSubscriber<{ data: number }>({
    topic: '/orbibot/min_obstacle_distance',
    messageType: 'std_msgs/Float32',
  });

  const { data: sectorsMsg } = useSubscriber<{ data: number[] }>({
    topic: '/orbibot/obstacle_sectors',
    messageType: 'std_msgs/Float32MultiArray',
  });

  const obstacleDetected = obstacleMsg?.data ?? false;
  const emergencyStop = emergencyMsg?.data ?? false;
  const minDistance = distanceMsg?.data ?? null;
  const sectorDistances = sectorsMsg?.data ?? null;

  // Determine overall status
  const status: SafetyStatus = !isConnected
    ? 'unknown'
    : emergencyStop
      ? 'emergency'
      : obstacleDetected
        ? 'warning'
        : 'clear';

  // Get display properties based on status
  const getStatusDisplay = () => {
    switch (status) {
      case 'emergency':
        return {
          icon: <XOctagon className="w-5 h-5" />,
          label: 'EMERGENCY',
          description: 'Obstacle too close!',
          bgColor: 'bg-red-500',
          textColor: 'text-white',
          borderColor: 'border-red-500',
          pulseClass: 'animate-pulse',
        };
      case 'warning':
        return {
          icon: <AlertTriangle className="w-5 h-5" />,
          label: 'WARNING',
          description: 'Obstacle detected',
          bgColor: 'bg-yellow-500',
          textColor: 'text-yellow-500',
          borderColor: 'border-yellow-500',
          pulseClass: '',
        };
      case 'clear':
        return {
          icon: <Check className="w-5 h-5" />,
          label: 'CLEAR',
          description: 'Path is clear',
          bgColor: 'bg-primary/20',
          textColor: 'text-white',
          borderColor: 'border-primary/30',
          pulseClass: '',
        };
      default:
        return {
          icon: <Shield className="w-5 h-5" />,
          label: 'UNKNOWN',
          description: 'Not connected',
          bgColor: 'bg-muted',
          textColor: 'text-muted-foreground',
          borderColor: 'border-muted',
          pulseClass: '',
        };
    }
  };

  const display = getStatusDisplay();

  // Compact mode - always show 8-sector radar
  if (compact) {
    if (!isConnected || !sectorDistances) {
      return (
        <div className={cn("glass-panel p-3 flex items-center justify-between", className)}>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Shield className="w-4 h-4" />
            <span className="text-sm font-medium">Obstacle Info</span>
          </div>
          <span className="text-xs text-muted-foreground">Offline</span>
        </div>
      );
    }

    return (
      <div className={cn('glass-panel p-3', display.pulseClass, className)}>
        {/* Header: Status + Min Distance */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium">Obstacle Info</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn('text-xs font-bold', display.textColor)}>{display.label}</span>
            {minDistance !== null && (
              <span
                className={cn(
                  'text-xs font-mono font-semibold',
                  minDistance < 0.25 ? 'text-red-500' : minDistance < 0.5 ? 'text-yellow-500' : 'text-white'
                )}
              >
                {minDistance.toFixed(2)}m
              </span>
            )}
          </div>
        </div>

        {/* 8-Sector Radar - Always Visible */}
        {sectorDistances && sectorDistances.length === 8 ? (
          <SectorRadar sectors={sectorDistances} />
        ) : (
          <div className="text-xs text-muted-foreground text-center py-4">
            No sector data
          </div>
        )}
      </div>
    );
  }

  // Badge variant - compact display
  if (variant === 'badge') {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-2 px-3 py-1.5 rounded-full',
          'text-sm font-medium transition-all',
          display.bgColor,
          display.textColor,
          display.pulseClass,
          className
        )}
      >
        {display.icon}
        <span>{display.label}</span>
      </div>
    );
  }

  // Panel variant - full display
  return (
    <div
      className={cn(
        'glass-panel p-4 transition-all',
        display.pulseClass,
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold">Obstacle Detection</h3>
        </div>
        <div
          className={cn(
            'flex items-center gap-2 px-2 py-1 rounded-full text-xs font-bold',
            display.bgColor,
            display.textColor
          )}
        >
          {display.icon}
          <span>{display.label}</span>
        </div>
      </div>

      {/* Status Details */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Status</span>
          <span className={cn('font-medium', display.textColor)}>
            {display.description}
          </span>
        </div>

        {minDistance !== null && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Min Distance</span>
            <span
              className={cn(
                'font-mono font-medium',
                minDistance < 0.25
                  ? 'text-red-500'
                  : minDistance < 0.5
                    ? 'text-yellow-500'
                    : 'text-green-500'
              )}
            >
              {minDistance.toFixed(2)}m
            </span>
          </div>
        )}
      </div>

      {/* 8-Sector Radar */}
      {sectorDistances && sectorDistances.length === 8 && (
        <div className="mt-3 pt-3 border-t">
          <div className="text-xs text-muted-foreground mb-2">Sector View</div>
          <SectorRadar sectors={sectorDistances} />
        </div>
      )}

      {/* Visual Distance Indicator */}
      {minDistance !== null && (
        <div className="mt-3 pt-3 border-t">
          <div className="text-xs text-muted-foreground mb-2">Safety Zones</div>
          <div className="relative h-3 bg-muted rounded-full overflow-hidden">
            {/* Emergency zone (0-0.25m) — matches obstacle_detector emergency_distance default */}
            <div
              className="absolute left-0 h-full bg-red-500/30"
              style={{ width: '12.5%' }}
            />
            {/* Warning zone (0.25-0.5m) — matches obstacle_detector warning_distance default */}
            <div
              className="absolute h-full bg-yellow-500/30"
              style={{ left: '12.5%', width: '12.5%' }}
            />
            {/* Clear zone (0.5m+) */}
            <div
              className="absolute h-full bg-green-500/30"
              style={{ left: '25%', width: '75%' }}
            />
            {/* Current distance marker */}
            <div
              className={cn(
                'absolute top-0 w-1 h-full rounded-full',
                minDistance < 0.25
                  ? 'bg-red-500'
                  : minDistance < 0.5
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              )}
              style={{
                left: `${Math.min((minDistance / 2) * 100, 100)}%`,
              }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
            <span>0m</span>
            <span>0.25m</span>
            <span>0.5m</span>
            <span>2m+</span>
          </div>
        </div>
      )}

      {/* Not connected warning */}
      {!isConnected && (
        <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-xs text-yellow-500 text-center">
            Connect to ROS to enable obstacle detection
          </p>
        </div>
      )}
    </div>
  );
}
