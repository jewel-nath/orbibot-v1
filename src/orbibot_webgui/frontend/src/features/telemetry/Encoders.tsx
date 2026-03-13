
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
