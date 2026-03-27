/**
 * RobotStatusHeader - Unified battery gauge + safety status in a single compact header.
 * Battery: horizontal bar with voltage + % inline.
 * Safety: only shows fault badges when a fault is active; shows ●OK when clear.
 * Replaces: SafetyStatusWidget + the battery row of SystemInfo.
 */

import { useBattery } from '@/hooks/useBattery';
import { useSafetyStatus } from '@/hooks/useSafetyStatus';
import { useRos } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';
import {
  Battery as BatteryIcon,
  BatteryWarning,
  ShieldAlert,
  AlertTriangle,
  Thermometer,
  Gauge,
} from 'lucide-react';

const GAUGE_COLORS: Record<string, string> = {
  full: 'bg-green-500',
  normal: 'bg-blue-500',
  low: 'bg-yellow-500',
  critical: 'bg-red-500',
};

const TEXT_COLORS: Record<string, string> = {
  full: 'text-green-500',
  normal: 'text-blue-400',
  low: 'text-yellow-500',
  critical: 'text-red-500',
};

interface RobotStatusHeaderProps {
  className?: string;
}

export function RobotStatusHeader({ className }: RobotStatusHeaderProps) {
  const { isConnected } = useRos();
  const battery = useBattery();
  const safety = useSafetyStatus();

  if (!isConnected) {
    return (
      <div className={cn('glass-panel px-3 py-2 flex items-center justify-between', className)}>
        <div className="flex items-center gap-2 text-muted-foreground">
          <BatteryIcon className="w-4 h-4" />
          <span className="text-xs font-semibold uppercase tracking-wide">Robot Status</span>
        </div>
        <span className="text-[10px] text-muted-foreground">Offline</span>
      </div>
    );
  }

  const hasFault = safety
    ? safety.emergency_stop || safety.low_battery || safety.hardware_fault ||
      safety.velocity_limit || safety.temperature_limit
    : false;

  const BattIcon = battery?.status === 'critical' || battery?.status === 'low'
    ? BatteryWarning : BatteryIcon;
  const battColor = battery ? TEXT_COLORS[battery.status] ?? 'text-foreground' : 'text-muted-foreground';
  const gaugeColor = battery ? GAUGE_COLORS[battery.status] ?? 'bg-muted' : 'bg-muted';
  const pct = battery ? Math.min(Math.max(battery.percentage, 0), 100) : 0;

  return (
    <div className={cn('glass-panel px-3 py-2 space-y-1.5', className)}>
      {/* Battery row */}
      <div className="flex items-center gap-2">
        <BattIcon className={cn('w-4 h-4 shrink-0', battColor)} />
        {/* Bar */}
        <div className="flex-1 h-2 bg-muted/30 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-500', gaugeColor)}
            style={{ width: `${pct}%` }}
          />
        </div>
        {/* Voltage + % */}
        <span className={cn('text-xs font-mono font-bold shrink-0', battColor)}>
          {battery ? `${battery.voltage.toFixed(1)}V` : '—'}
        </span>
        <span className="text-[10px] text-muted-foreground shrink-0">
          {battery ? `${battery.percentage.toFixed(0)}%` : ''}
        </span>
      </div>

      {/* Safety row */}
      <div className="flex flex-wrap items-center gap-1.5 min-h-[18px]">
        {!safety && (
          <span className="text-[10px] text-muted-foreground">Safety offline</span>
        )}
        {safety && !hasFault && (
          <span className="flex items-center gap-1 text-[10px] text-green-500 font-medium">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500" />
            {safety.motors_disabled ? 'Motors off' : 'All systems OK'}
          </span>
        )}
        {safety?.emergency_stop && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-500 border border-red-500/40">
            <ShieldAlert className="w-3 h-3" /> E-stop
          </span>
        )}
        {safety?.low_battery && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-500 border border-amber-500/40">
            <BatteryWarning className="w-3 h-3" /> Low batt
          </span>
        )}
        {safety?.hardware_fault && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-500/20 text-red-500 border border-red-500/40">
            <AlertTriangle className="w-3 h-3" /> HW Fault
          </span>
        )}
        {safety?.temperature_limit && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/20 text-amber-500 border border-amber-500/40">
            <Thermometer className="w-3 h-3" /> Temp
          </span>
        )}
        {safety?.velocity_limit && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] text-muted-foreground border border-border">
            <Gauge className="w-3 h-3" /> V-limit
          </span>
        )}
        {safety?.fault_code !== undefined && safety.fault_code !== 0 && (
          <span className="text-[10px] font-mono text-muted-foreground">#{safety.fault_code}</span>
        )}
      </div>
    </div>
  );
}
