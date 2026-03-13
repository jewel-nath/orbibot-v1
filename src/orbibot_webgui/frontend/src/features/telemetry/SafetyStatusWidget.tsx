/**
 * SafetyStatusWidget - Compact display of safety flags.
 * E-stop: only when robot enters emergency (e.g. critical battery), not when user clicks STOP.
 * Motors off: shown when motors are disabled (e.g. after clicking STOP in header).
 */

import { useSafetyStatus } from '@/hooks/useSafetyStatus';
import { useRos } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';
import { ShieldAlert, BatteryWarning, AlertTriangle, Gauge, Thermometer } from 'lucide-react';

interface SafetyStatusWidgetProps {
  className?: string;
}

export function SafetyStatusWidget({ className }: SafetyStatusWidgetProps) {
  const { isConnected } = useRos();
  const safety = useSafetyStatus();

  if (!isConnected || !safety) {
    return (
      <div className={cn('glass-panel p-3 flex items-center justify-between', className)}>
        <div className="flex items-center gap-2 text-muted-foreground">
          <ShieldAlert className="w-4 h-4" />
          <span className="text-sm font-medium">Safety</span>
        </div>
        <span className="text-xs text-muted-foreground">Offline</span>
      </div>
    );
  }

  // Only show faults that need user action. cmd_timeout when idle is normal (no /cmd_vel).
  const hasFault =
    safety.emergency_stop ||
    safety.low_battery ||
    safety.hardware_fault ||
    safety.velocity_limit ||
    safety.temperature_limit;

  return (
    <div className={cn('glass-panel p-3', className)}>
      <div className="flex items-center gap-2 mb-2">
        <ShieldAlert className={cn('w-4 h-4', hasFault ? 'text-amber-500' : 'text-primary')} />
        <span className="text-sm font-medium">Safety</span>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {safety.emergency_stop && (
          <span
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-500 border border-red-500/40"
            title="Emergency stop"
          >
            <ShieldAlert className="w-3 h-3" /> E-stop
          </span>
        )}
        {safety.low_battery && (
          <span
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/40"
            title="Low battery"
          >
            <BatteryWarning className="w-3 h-3" /> Low batt
          </span>
        )}
        {safety.hardware_fault && (
          <span
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-500/20 text-red-500 border border-red-500/40"
            title="Hardware fault"
          >
            <AlertTriangle className="w-3 h-3" /> Fault
          </span>
        )}
        {safety.velocity_limit && (
          <span
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground border border-border"
            title="Velocity limit"
          >
            <Gauge className="w-3 h-3" /> V-limit
          </span>
        )}
        {safety.temperature_limit && (
          <span
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/40"
            title="Temperature limit"
          >
            <Thermometer className="w-3 h-3" /> Temp
          </span>
        )}
        {!hasFault && (
          <span className="text-[10px] text-muted-foreground font-medium" title={safety.motors_disabled ? 'Motors disabled (e.g. via STOP button)' : 'All clear'}>
            {safety.motors_disabled ? 'Motors off' : 'OK'}
          </span>
        )}
        {safety.fault_code !== 0 && (
          <span className="text-[10px] font-mono text-muted-foreground" title="Fault code">
            #{safety.fault_code}
          </span>
        )}
      </div>
    </div>
  );
}
