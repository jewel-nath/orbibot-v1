
import { useMotors } from '@/hooks/useMotors';
import { cn } from '@/lib/utils';
import { Gauge } from 'lucide-react';
import { useRos } from '@/contexts/RosContext';

interface EncodersProps {
    className?: string;
}

export function Encoders({ className }: EncodersProps) {
    const { isConnected } = useRos();
    const motors = useMotors();

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

    return (
        <div className={cn('glass-panel p-3', className)}>
            <div className="flex items-center gap-2 mb-3">
                <Gauge className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">Encoders</span>
            </div>

            <div className="grid grid-cols-4 gap-2">
                {motors.map((motor) => (
                    <div
                        key={motor.id}
                        className={cn(
                            'p-2 rounded-md border text-center',
                            motor.enabled
                                ? 'bg-primary/10 border-primary/20 text-foreground'
                                : 'bg-muted/30 border-border/30 text-muted-foreground'
                        )}
                    >
                        <div className="text-[10px] font-bold uppercase opacity-70">{motor.abbreviation}</div>
                        <div className="font-mono text-[10px] font-bold leading-tight mt-0.5 truncate">
                            {motor.encoderCount}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
