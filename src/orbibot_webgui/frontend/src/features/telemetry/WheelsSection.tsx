/**
 * WheelsSection - Collapsible wheel status with robot silhouette SVG.
 * Shows top-down robot with 4 color-coded wheels + encoder counts per wheel.
 * Reset encoders button at the bottom.
 */

import { useState, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useMotors } from '@/hooks/useMotors';
import { useRos, useRosContext } from '@/contexts/RosContext';
import { SectionHeader, RobotSilhouette } from './components';
import { cn } from '@/lib/utils';
import { Cog, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WheelsSectionProps {
  className?: string;
}

export function WheelsSection({ className }: WheelsSectionProps) {
  const { isConnected } = useRos();
  const { ros, connectionState } = useRosContext();
  const motors = useMotors();
  const [isResetting, setIsResetting] = useState(false);
  const [resetFeedback, setResetFeedback] = useState<'idle' | 'success' | 'error'>('idle');

  const handleReset = useCallback(() => {
    if (!ros || connectionState !== 'connected') return;
    setIsResetting(true);
    setResetFeedback('idle');
    const svc = new ROSLIB.Service({ ros, name: '/orbibot/reset_encoders', serviceType: 'orbibot_msgs/srv/ResetEncoders' });
    svc.callService(
      new ROSLIB.ServiceRequest({}),
      (res: { success: boolean }) => {
        setIsResetting(false);
        setResetFeedback(res.success ? 'success' : 'error');
        if (res.success) setTimeout(() => setResetFeedback('idle'), 2000);
      },
      () => { setIsResetting(false); setResetFeedback('error'); setTimeout(() => setResetFeedback('idle'), 2000); }
    );
  }, [ros, connectionState]);

  // Map MotorState → WheelData for RobotSilhouette
  const wheels = motors?.map(m => ({
    id: m.id,
    label: m.abbreviation,
    encoderCount: m.encoderCount,
    enabled: m.enabled,
  })) ?? [];

  return (
    <SectionHeader
      icon={Cog}
      title="Wheels"
      defaultOpen={false}
      className={className}
    >
      {!isConnected || !motors ? (
        <div className="text-[10px] text-muted-foreground py-1">
          {!isConnected ? 'Offline' : 'Waiting for motor data…'}
        </div>
      ) : (
        <div className="space-y-2">
          {/* Robot silhouette */}
          <div className="flex justify-center">
            <RobotSilhouette wheels={wheels} width={148} />
          </div>

          {/* Encoder count table */}
          <div className="grid grid-cols-4 gap-1 text-center">
            {motors.map(m => (
              <div key={m.id} className="space-y-0.5">
                <div className={cn(
                  'text-[9px] font-semibold',
                  m.enabled ? 'text-green-500' : 'text-muted-foreground'
                )}>
                  {m.abbreviation}
                </div>
                <div className="font-mono text-[10px] text-foreground">
                  {m.encoderCount.toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          {/* Feedback + reset */}
          {resetFeedback === 'success' && (
            <p className="text-[10px] text-green-500">Encoders reset</p>
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
            {isResetting ? 'Resetting…' : 'Reset encoders'}
          </Button>
        </div>
      )}
    </SectionHeader>
  );
}
