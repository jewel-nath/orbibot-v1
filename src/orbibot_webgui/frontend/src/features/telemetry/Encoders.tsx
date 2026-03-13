import { useState, useCallback } from 'react';
import ROSLIB from 'roslib';
import { useMotors } from '@/hooks/useMotors';
import { cn } from '@/lib/utils';
import { Gauge, RotateCcw } from 'lucide-react';
import { useRos, useRosContext } from '@/contexts/RosContext';
import { Button } from '@/components/ui/button';

interface EncodersProps {
    className?: string;
}

export function Encoders({ className }: EncodersProps) {
    const { isConnected } = useRos();
    const { ros, connectionState } = useRosContext();
    const motors = useMotors();
    const [isResetting, setIsResetting] = useState(false);
    const [resetFeedback, setResetFeedback] = useState<'idle' | 'success' | 'error'>('idle');

    const handleResetEncoders = useCallback(() => {
        if (!ros || connectionState !== 'connected') return;
        setIsResetting(true);
        setResetFeedback('idle');
        const service = new ROSLIB.Service({
            ros,
            name: '/orbibot/reset_encoders',
            serviceType: 'orbibot_msgs/srv/ResetEncoders',
        });
        const request = new ROSLIB.ServiceRequest({});
        service.callService(
            request,
            (response: { success: boolean; message: string }) => {
                setIsResetting(false);
                setResetFeedback(response.success ? 'success' : 'error');
                if (response.success) setTimeout(() => setResetFeedback('idle'), 2000);
            },
            (_error: string) => {
                setIsResetting(false);
                setResetFeedback('error');
                setTimeout(() => setResetFeedback('idle'), 2000);
            }
        );
    }, [ros, connectionState]);

    if (!isConnected || !motors) {
        return (
            <div className={cn("glass-panel p-3 flex items-center justify-between", className)}>
                <div className="flex items-center gap-2 text-muted-foreground">
                    <Gauge className="w-4 h-4" />
                    <span className="text-sm font-medium">Encoders</span>
                </div>
                <span className="text-xs text-muted-foreground">Offline</span>
            </div>
        );
    }

    const serviceAvailable = connectionState === 'connected' && !!ros;

    return (
        <div className={cn('glass-panel p-3', className)}>
            <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium">Encoders</span>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-5 min-w-0 px-1.5 text-[10px] font-normal"
                    onClick={handleResetEncoders}
                    disabled={!serviceAvailable || isResetting}
                    title="Reset encoder counts to zero (odometry unchanged)"
                >
                    <RotateCcw className={cn('w-3 h-3 mr-0.5 shrink-0', isResetting && 'animate-spin')} />
                    {isResetting ? '…' : 'Reset'}
                </Button>
            </div>
            {resetFeedback === 'success' && (
                <p className="text-xs text-green-600 dark:text-green-400 mb-1">Encoders reset</p>
            )}
            {resetFeedback === 'error' && (
                <p className="text-xs text-destructive mb-1">Reset failed</p>
            )}
            <div className="flex items-center justify-between gap-3 text-xs">
                {motors.map((motor) => (
                    <div key={motor.id} className="text-center flex-1 min-w-0">
                        <span className="text-muted-foreground">{motor.abbreviation}</span>
                        <span className="ml-1 font-mono font-semibold">{motor.encoderCount}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
