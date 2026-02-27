/**
 * SystemHealth - Enhanced system health monitoring with visual gauges
 * Shows CPU, RAM, Disk, Temperature, and Battery in a clean visual layout
 */

import { useSystemStatus } from '@/hooks/useSystemStatus';
import { useBattery } from '@/hooks/useBattery';
import { cn } from '@/lib/utils';
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Thermometer, 
  Battery as BatteryIcon, 
  BatteryWarning,
  AlertTriangle
} from 'lucide-react';
import { useRos } from '@/contexts/RosContext';

interface GaugeBarProps {
  value: number;
  max?: number;
  label: string;
  icon: React.ReactNode;
  unit?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  compact?: boolean;
}

function GaugeBar({ 
  value, 
  max = 100, 
  label, 
  icon, 
  unit = '%',
  warningThreshold = 70,
  criticalThreshold = 90,
  compact = false 
}: GaugeBarProps) {
  const percentage = Math.min((value / max) * 100, 100);
  
  const getColor = () => {
    if (percentage >= criticalThreshold) return 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]';
    if (percentage >= warningThreshold) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div className="text-muted-foreground">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-center mb-0.5">
            <span className="text-[10px] text-muted-foreground uppercase">{label}</span>
            <span className={cn(
              "text-[10px] font-bold font-mono",
              percentage >= criticalThreshold ? "text-red-500" : 
              percentage >= warningThreshold ? "text-yellow-500" : "text-foreground"
            )}>
              {value.toFixed(0)}{unit}
            </span>
          </div>
          <div className="h-1 bg-muted/30 rounded-full overflow-hidden">
            <div 
              className={cn("h-full rounded-full transition-all duration-500", getColor())}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          {icon}
          <span className="text-xs">{label}</span>
        </div>
        <span className={cn(
          "text-xs font-bold font-mono",
          percentage >= criticalThreshold ? "text-red-500" : 
          percentage >= warningThreshold ? "text-yellow-500" : "text-foreground"
        )}>
          {value.toFixed(0)}{unit}
        </span>
      </div>
      <div className="h-2 bg-muted/30 rounded-full overflow-hidden">
        <div 
          className={cn("h-full rounded-full transition-all duration-500", getColor())}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface SystemHealthProps {
  className?: string;
}

export function SystemHealth({ className }: SystemHealthProps) {
  const { isConnected } = useRos();
  const status = useSystemStatus();
  const battery = useBattery();

  if (!isConnected) {
    return (
      <div className={cn("glass-panel p-3", className)}>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Activity className="w-4 h-4" />
          <span className="text-sm font-medium">System Health</span>
          <span className="text-xs ml-auto">Offline</span>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className={cn("glass-panel p-3", className)}>
        <div className="flex items-center gap-2 text-muted-foreground animate-pulse">
          <Activity className="w-4 h-4" />
          <span className="text-sm font-medium">System Health</span>
          <span className="text-xs ml-auto">Loading...</span>
        </div>
      </div>
    );
  }

  // Battery status
  const batteryPercentage = battery?.percentage ?? 0;
  const batteryVoltage = battery?.voltage ?? 0;
  const batteryStatus = battery?.status ?? 'unknown';
  
  const getBatteryColor = () => {
    if (batteryStatus === 'critical' || batteryVoltage < 10.5) return 'text-red-500';
    if (batteryStatus === 'low' || batteryVoltage < 11.0) return 'text-yellow-500';
    if (batteryStatus === 'full') return 'text-green-500';
    return 'text-blue-500';
  };

  const getBatteryIcon = () => {
    if (batteryStatus === 'critical' || batteryVoltage < 10.5) {
      return <BatteryWarning className="w-4 h-4 text-red-500" />;
    }
    return <BatteryIcon className={cn("w-4 h-4", getBatteryColor())} />;
  };

  // Check for any critical alerts
  const hasCriticalTemp = status.cpu_temp > 80;
  const hasCriticalCPU = status.cpu_percent > 90;
  const hasCriticalRAM = status.ram_percent > 90;
  const hasCriticalDisk = status.disk_percent > 90;
  const hasCriticalBattery = batteryVoltage < 10.5;
  
  const hasAnyCritical = hasCriticalTemp || hasCriticalCPU || hasCriticalRAM || hasCriticalDisk || hasCriticalBattery;

  return (
    <div className={cn("glass-panel overflow-hidden", className)}>
      {/* Header with alert indicator */}
      <div className={cn(
        "px-3 py-2 flex items-center gap-2 border-b",
        hasAnyCritical ? "bg-red-500/10 border-red-500/20" : "bg-primary/5 border-border/50"
      )}>
        {hasAnyCritical ? (
          <AlertTriangle className="w-4 h-4 text-red-500 animate-pulse" />
        ) : (
          <Activity className="w-4 h-4 text-primary" />
        )}
        <span className={cn(
          "text-sm font-medium",
          hasAnyCritical ? "text-red-500" : "text-foreground"
        )}>
          System Health
        </span>
        {hasAnyCritical && (
          <span className="text-[10px] text-red-500 font-bold ml-auto">ALERT</span>
        )}
      </div>

      <div className="p-3 space-y-3">
        {/* Battery Section */}
        <div className="flex items-center gap-3 pb-3 border-b border-border/30">
          <div className="relative">
            {getBatteryIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex justify-between items-center">
              <span className="text-xs text-muted-foreground">Battery</span>
              <span className={cn("text-sm font-bold font-mono", getBatteryColor())}>
                {batteryVoltage.toFixed(2)}V
              </span>
            </div>
            <div className="h-2 bg-muted/30 rounded-full overflow-hidden mt-1">
              <div 
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  batteryStatus === 'critical' || batteryVoltage < 10.5 ? "bg-red-500" :
                  batteryStatus === 'low' || batteryVoltage < 11.0 ? "bg-yellow-500" :
                  "bg-green-500"
                )}
                style={{ width: `${Math.min(Math.max(batteryPercentage, 0), 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Gauges Grid */}
        <div className="space-y-2">
          <GaugeBar
            value={status.cpu_percent}
            label="CPU"
            icon={<Cpu className="w-3 h-3" />}
            warningThreshold={70}
            criticalThreshold={90}
            compact
          />
          <GaugeBar
            value={status.ram_percent}
            label="RAM"
            icon={<Activity className="w-3 h-3" />}
            warningThreshold={80}
            criticalThreshold={95}
            compact
          />
          <GaugeBar
            value={status.disk_percent}
            label="Disk"
            icon={<HardDrive className="w-3 h-3" />}
            warningThreshold={85}
            criticalThreshold={95}
            compact
          />
          <GaugeBar
            value={status.cpu_temp}
            max={100}
            label="Temp"
            icon={<Thermometer className="w-3 h-3" />}
            unit="°C"
            warningThreshold={70}
            criticalThreshold={85}
            compact
          />
        </div>

        {/* Hardware Status */}
        <div className="pt-2 border-t border-border/30 flex items-center justify-between">
          <span className="text-[10px] text-muted-foreground">Hardware</span>
          <div className="flex items-center gap-1.5">
            <div className={cn(
              "w-2 h-2 rounded-full",
              status.hardware_ok 
                ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" 
                : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]"
            )} />
            <span className={cn(
              "text-[10px] font-bold",
              status.hardware_ok ? "text-green-500" : "text-red-500"
            )}>
              {status.hardware_ok ? "ONLINE" : "ERROR"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}