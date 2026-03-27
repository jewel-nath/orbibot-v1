/**
 * PositionSection - Collapsible position & heading section.
 * Left: CompassRose SVG driven by IMU yaw.
 * Right: X / Y / θ from odometry + distance from origin.
 * Reset odometry button at the bottom.
 */

import { useState, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useOdometry } from '@/hooks/useOdometry';
import { useIMU } from '@/hooks/useIMU';
import { useRos, useRosContext } from '@/contexts/RosContext';
import { useSettings } from '@/contexts/SettingsContext';
import { SectionHeader, CompassRose } from './components';
import { cn } from '@/lib/utils';
import { MapPin, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

function odomSourceLabel(topic: string) {
  return topic === '/odometry/filtered' ? 'Fused' : 'Wheel';
}

interface PositionSectionProps {
  className?: string;
}

export function PositionSection({ className }: PositionSectionProps) {
  const { isConnected } = useRos();
  const { ros, connectionState } = useRosContext();
  const { settings } = useSettings();
  const odom = useOdometry();
  const imu = useIMU();
  const [isResetting, setIsResetting] = useState(false);
  const [resetFeedback, setResetFeedback] = useState<'idle' | 'success' | 'error'>('idle');

  const handleReset = useCallback(() => {
    if (!ros || connectionState !== 'connected') return;
    setIsResetting(true);
    setResetFeedback('idle');
    const svc = new ROSLIB.Service({ ros, name: '/orbibot/reset_odometry', serviceType: 'orbibot_msgs/srv/ResetOdometry' });
    const req = new ROSLIB.ServiceRequest({ reset_pose: { position: { x: 0, y: 0, z: 0 }, orientation: { x: 0, y: 0, z: 0, w: 1 } } });
    svc.callService(
      req,
      (res: { success: boolean }) => {
        setIsResetting(false);
        setResetFeedback(res.success ? 'success' : 'error');
        if (res.success) setTimeout(() => setResetFeedback('idle'), 2000);
      },
      () => { setIsResetting(false); setResetFeedback('error'); setTimeout(() => setResetFeedback('idle'), 2000); }
    );
  }, [ros, connectionState]);

  const sourceBadge = odom ? (
    <span className="text-[9px] text-muted-foreground ml-1 shrink-0">
      ({odomSourceLabel(settings.odomTopic)})
    </span>
  ) : undefined;

  return (
    <SectionHeader
      icon={MapPin}
      title="Position"
      badge={sourceBadge}
      defaultOpen
      className={className}
    >
      {!isConnected || (!odom && !imu) ? (
        <div className="text-[10px] text-muted-foreground py-1">
          {!isConnected ? 'Offline' : 'Waiting for odometry…'}
        </div>
      ) : (
        <div className="space-y-2">
          {/* Compass + Position values */}
          <div className="flex items-start gap-3">
            {/* Compass: driven by IMU yaw, falls back to odometry theta */}
            <CompassRose
              heading={imu?.yaw ?? odom?.theta ?? 0}
              size={88}
            />
            {/* Position values */}
            <div className="flex-1 min-w-0 space-y-1.5 pt-1">
              {[
                { label: 'X', value: odom ? `${odom.x.toFixed(2)} m` : '—' },
                { label: 'Y', value: odom ? `${odom.y.toFixed(2)} m` : '—' },
                { label: 'θ', value: odom ? `${odom.theta.toFixed(1)}°` : imu ? `${imu.yaw.toFixed(1)}°` : '—' },
                { label: 'Dist', value: odom ? `${Math.sqrt(odom.x ** 2 + odom.y ** 2).toFixed(2)} m` : '—' },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-baseline justify-between gap-1">
                  <span className="text-[10px] text-muted-foreground w-7 shrink-0">{label}</span>
                  <span className="font-mono text-xs font-semibold">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Reset feedback + button */}
          {resetFeedback === 'success' && (
            <p className="text-[10px] text-green-500">Odometry reset</p>
          )}
          {resetFeedback === 'error' && (
            <p className="text-[10px] text-destructive">Reset failed</p>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-full text-[10px] font-normal"
            onClick={handleReset}
            disabled={!isConnected || connectionState !== 'connected' || isResetting}
          >
            <RotateCcw className={cn('w-3 h-3 mr-1 shrink-0', isResetting && 'animate-spin')} />
            {isResetting ? 'Resetting…' : 'Reset odometry'}
          </Button>
        </div>
      )}
    </SectionHeader>
  );
}
