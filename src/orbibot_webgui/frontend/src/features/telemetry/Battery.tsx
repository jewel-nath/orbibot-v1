
import { useBattery } from '@/hooks/useBattery';
import { BATTERY_PARAMS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { Battery as BatteryIcon, BatteryWarning } from 'lucide-react';
import { Widget } from '@/components/ui/Widget';
import { useRos } from '@/contexts/RosContext';

interface BatteryProps {
    className?: string;
    compact?: boolean;
}

export function Battery({ className, compact = false }: BatteryProps) {
    const { isConnected } = useRos();
    const battery = useBattery();

    // Color coding based on battery status
    const statusColors = {
        full: 'text-green-500 bg-green-500/10 border-green-500/20',
        normal: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
        low: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20',
        critical: 'text-red-500 bg-red-500/10 border-red-500/20',
    };

    const gaugeColors = {
        full: 'bg-green-500',
        normal: 'bg-blue-500',
        low: 'bg-yellow-500',
        critical: 'bg-red-500',
    };

    // If compact, we render a minimal version without the Widget wrapper for sidebar usage
    // OR we can make the Widget support compact mode. Let's use Widget for consistency but adapt content.

    if (compact) {
        if (!isConnected || !battery) {
            return (
                <div className={cn("glass-panel p-3 flex items-center justify-between", className)}>
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <BatteryIcon className="w-4 h-4" />
                        <span className="text-sm font-medium">Battery</span>
                    </div>
                    <span className="text-xs text-muted-foreground">Offline</span>
                </div>
            );
        }

        const Icon = battery.status === 'critical' || battery.status === 'low' ? BatteryWarning : BatteryIcon;
        const percentageWidth = Math.min(Math.max(battery.percentage, 0), 100);

        return (
            <div className={cn("glass-panel p-3 relative overflow-hidden", className)}>
                <div className="flex items-center justify-between gap-3 relative z-10">
                    <div className="flex items-center gap-2">
                        <Icon className={cn("w-4 h-4", statusColors[battery.status].split(' ')[0])} />
                        <span className="text-sm font-medium">Battery</span>
                    </div>
                    <div className="flex items-center gap-3 flex-1 justify-end">
                        {/* Progress Bar */}
                        <div className="w-24 h-1.5 bg-muted/20 rounded-full overflow-hidden">
                            <div
                                className={cn("h-full transition-all duration-500", gaugeColors[battery.status])}
                                style={{ width: `${percentageWidth}%` }}
                            />
                        </div>
                        <span className="font-mono text-sm font-bold">{battery.voltage.toFixed(1)}V</span>
                    </div>
                </div>
                {/* Background Gradient for status */}
                <div className={cn("absolute inset-0 opacity-5 pointer-events-none", gaugeColors[battery.status])} />
            </div>
        );
    }

    // Full Widget Mode
    const Icon = battery?.status && (battery.status === 'critical' || battery.status === 'low') ? BatteryWarning : BatteryIcon;
    const percentageWidth = battery ? Math.min(Math.max(battery.percentage, 0), 100) : 0;

    return (
        <Widget
            title="Power System"
            icon={Icon}
            className={className}
            loading={isConnected && !battery}
            empty={!isConnected}
            emptyMessage="Robot disconnected"
        >
            {battery && (
                <div className="space-y-6">
                    {/* Main Status Display */}
                    <div className="flex flex-col items-center justify-center py-2">
                        <div className="relative">
                            <span className="text-5xl font-bold tracking-tighter text-foreground">
                                {battery.voltage.toFixed(1)}
                                <span className="text-2xl text-muted-foreground ml-1">V</span>
                            </span>
                        </div>
                        <div className={cn(
                            "mt-2 px-3 py-1 rounded-full text-xs font-medium border uppercase tracking-wider",
                            statusColors[battery.status]
                        )}>
                            {battery.status} ({battery.percentage.toFixed(0)}%)
                        </div>
                    </div>

                    {/* Large Progress Bar */}
                    <div className="space-y-1">
                        <div className="flex justify-between text-xs text-muted-foreground">
                            <span>0%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                        <div className="h-4 bg-muted/20 rounded-full overflow-hidden border border-white/5">
                            <div
                                className={cn("h-full transition-all duration-700 ease-out shadow-[0_0_10px_rgba(0,0,0,0.2)]", gaugeColors[battery.status])}
                                style={{ width: `${percentageWidth}%` }}
                            />
                        </div>
                    </div>

                    {/* Diagnostics Grid */}
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/40">
                        <div className="space-y-1">
                            <span className="text-xs text-muted-foreground">Low Warning</span>
                            <div className="font-mono text-sm text-yellow-500">{BATTERY_PARAMS.lowThreshold}V</div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs text-muted-foreground">Critical Cutoff</span>
                            <div className="font-mono text-sm text-red-500">{BATTERY_PARAMS.criticalThreshold}V</div>
                        </div>
                    </div>

                    {/* Critical Warning */}
                    {battery.status === 'critical' && (
                        <div className="p-3 rounded bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold flex items-center gap-2 animate-pulse">
                            <BatteryWarning className="w-4 h-4" />
                            CRITICAL VOLTAGE - CHARGE IMMEDIATELY
                        </div>
                    )}
                </div>
            )}
        </Widget>
    );
}
