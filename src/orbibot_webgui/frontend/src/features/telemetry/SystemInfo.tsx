
import { useSystemStatus } from '@/hooks/useSystemStatus';
import { useBattery } from '@/hooks/useBattery';
import { cn } from '@/lib/utils';
import { Activity, Cpu, HardDrive, Thermometer, Battery as BatteryIcon, BatteryWarning } from 'lucide-react';
import { Widget } from '@/components/ui/Widget';
import { useRos } from '@/contexts/RosContext';

interface CircularProgressProps {
    value: number;
    max?: number;
    size?: number;
    strokeWidth?: number;
    className?: string;
    label?: string;
    icon?: React.ReactNode;
    unit?: string;
}

function CircularProgress({
    value,
    max = 100,
    size = 56,
    strokeWidth = 4,
    className,
    label,
    icon,
    unit = '%',
}: CircularProgressProps) {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const normalizedValue = Math.min(value / max, 1);
    const offset = circumference - normalizedValue * circumference;

    // Color based on value
    const getColor = () => {
        if (normalizedValue >= 0.9) return 'text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]';
        if (normalizedValue >= 0.7) return 'text-yellow-500';
        return 'text-primary drop-shadow-[0_0_8px_rgba(59,130,246,0.3)]';
    };

    return (
        <div className={cn('flex flex-col items-center gap-2 group', className)}>
            <div className="relative flex items-center justify-center">
                <svg className="transform -rotate-90 transition-all duration-300" width={size} height={size}>
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        stroke="currentColor"
                        strokeWidth={strokeWidth}
                        fill="none"
                        className="text-muted/10"
                    />
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        stroke="currentColor"
                        strokeWidth={strokeWidth}
                        fill="none"
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        strokeLinecap="round"
                        className={cn('transition-all duration-500 ease-out', getColor())}
                    />
                </svg>

                {/* Center icon */}
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground group-hover:text-foreground transition-colors">
                    {icon}
                </div>
            </div>

            <div className='text-center'>
                <div className={cn("text-sm font-bold font-mono", getColor())}>
                    {value.toFixed(0)}{unit}
                </div>
                {label && <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{label}</div>}
            </div>
        </div>
    );
}

interface SystemInfoProps {
    className?: string;
    compact?: boolean;
}

export function SystemInfo({ className, compact = false }: SystemInfoProps) {
    const { isConnected } = useRos();
    const status = useSystemStatus();
    const battery = useBattery();

    // Compact mode for sidebar - show CPU/RAM/DISK/TEMP/Battery
    if (compact) {
        if (!isConnected || !status) {
            return (
                <div className={cn("glass-panel p-3 flex items-center justify-between", className)}>
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <Activity className="w-4 h-4" />
                        <span className="text-sm font-medium">System</span>
                    </div>
                    <span className="text-xs text-muted-foreground">Offline</span>
                </div>
            );
        }

        // Battery status colors
        const batteryColor = battery
            ? battery.status === 'critical'
                ? 'text-red-500'
                : battery.status === 'low'
                    ? 'text-yellow-500'
                    : battery.status === 'full'
                        ? 'text-green-500'
                        : 'text-foreground'
            : 'text-muted-foreground';

        return (
            <div className={cn("glass-panel p-3", className)}>
                <div className="flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium">System Health</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                    {/* Row 1 */}
                    <div className="text-center">
                        <span className="block text-[10px] text-muted-foreground">CPU</span>
                        <span className={cn("text-xs font-bold font-mono", status.cpu_percent > 80 ? "text-red-500" : "text-foreground")}>
                            {status.cpu_percent.toFixed(0)}%
                        </span>
                    </div>
                    <div className="text-center">
                        <span className="block text-[10px] text-muted-foreground">RAM</span>
                        <span className="text-xs font-bold font-mono">{status.ram_percent.toFixed(0)}%</span>
                    </div>
                    <div className="text-center">
                        <span className="block text-[10px] text-muted-foreground">BATT</span>
                        <span className={cn("text-xs font-bold font-mono", batteryColor)}>
                            {battery ? battery.voltage.toFixed(1) : 'N/A'}V
                        </span>
                    </div>
                    {/* Row 2 */}
                    <div className="text-center">
                        <span className="block text-[10px] text-muted-foreground">DISK</span>
                        <span className="text-xs font-bold font-mono">{status.disk_percent.toFixed(0)}%</span>
                    </div>
                    <div className="text-center">
                        <span className="block text-[10px] text-muted-foreground">TEMP</span>
                        <span className="text-xs font-bold font-mono">{status.cpu_temp.toFixed(0)}°</span>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <Widget
            title="System Diagnostics"
            icon={Activity}
            className={className}
            loading={isConnected && !status}
            empty={!isConnected}
            emptyMessage="System Monitor Offline"
        >
            {status && (
                <div className="space-y-6">
                    <div className="grid grid-cols-4 gap-4">
                        <CircularProgress
                            value={status.cpu_percent ?? 0}
                            label="CPU Load"
                            icon={<Cpu className="w-4 h-4" />}
                        />
                        <CircularProgress
                            value={status.ram_percent ?? 0}
                            label="Memory"
                            icon={<Activity className="w-4 h-4" />}
                        />
                        <CircularProgress
                            value={status.cpu_temp ?? 0}
                            max={85}
                            label="Core Temp"
                            icon={<Thermometer className="w-4 h-4" />}
                            unit="°C"
                        />
                        <CircularProgress
                            value={status.disk_percent ?? 0}
                            label="Storage"
                            icon={<HardDrive className="w-4 h-4" />}
                        />
                    </div>

                    <div className="pt-4 border-t border-border/40 grid grid-cols-2 gap-4">
                        <div className="bg-card/40 p-3 rounded-lg">
                            <div className="flex items-center gap-2 text-muted-foreground mb-2">
                                {battery && (battery.status === 'critical' || battery.status === 'low') ? (
                                    <BatteryWarning className="w-4 h-4 text-yellow-500" />
                                ) : (
                                    <BatteryIcon className="w-4 h-4 text-green-500" />
                                )}
                                <span className="text-xs font-medium">Battery</span>
                            </div>
                            {battery ? (
                                <div className="space-y-1">
                                    <div className="flex items-baseline justify-between">
                                        <span className="font-mono font-bold text-lg text-foreground">
                                            {battery.voltage.toFixed(2)}V
                                        </span>
                                        <span className={cn(
                                            "text-xs font-bold uppercase",
                                            battery.status === 'critical' ? 'text-red-500' :
                                            battery.status === 'low' ? 'text-yellow-500' :
                                            battery.status === 'full' ? 'text-green-500' :
                                            'text-foreground'
                                        )}>
                                            {battery.status} ({battery.percentage.toFixed(0)}%)
                                        </span>
                                    </div>
                                    <div className="h-1.5 bg-muted/20 rounded-full overflow-hidden">
                                        <div
                                            className={cn(
                                                "h-full transition-all duration-500",
                                                battery.status === 'critical' ? 'bg-red-500' :
                                                battery.status === 'low' ? 'bg-yellow-500' :
                                                battery.status === 'full' ? 'bg-green-500' :
                                                'bg-blue-500'
                                            )}
                                            style={{ width: `${Math.min(Math.max(battery.percentage, 0), 100)}%` }}
                                        />
                                    </div>
                                </div>
                            ) : (
                                <span className="font-mono font-bold text-foreground">N/A</span>
                            )}
                        </div>

                        <div className="bg-card/40 p-3 rounded-lg flex items-center justify-between">
                            <div className="flex items-center gap-2 text-muted-foreground">
                                <Activity className="w-4 h-4" />
                                <span className="text-xs font-medium">Status</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className={cn("w-2 h-2 rounded-full", status.hardware_ok ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-red-500")} />
                                <span className="text-xs font-bold">
                                    {status.hardware_ok ? "ONLINE" : "ERROR"}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Widget>
    );
}
