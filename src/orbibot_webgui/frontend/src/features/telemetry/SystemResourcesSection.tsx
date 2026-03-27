/**
 * SystemResourcesSection - Collapsible system resource gauges with sparkline trends.
 * CPU / RAM / Temp: GaugeBar + Sparkline side-by-side.
 * Disk: GaugeBar only (changes too slowly to trend meaningfully at 1Hz).
 */

import { useSystemStatus } from '@/hooks/useSystemStatus';
import { useRos } from '@/contexts/RosContext';
import { useTimeSeriesBuffer } from '@/hooks/useTimeSeriesBuffer';
import { SectionHeader, Sparkline } from './components';
import { cn } from '@/lib/utils';
import { Activity, Cpu, Thermometer, HardDrive } from 'lucide-react';

// ── Inline GaugeBar (matches SystemHealth.tsx pattern) ──────────────────────
interface GaugeBarProps {
  value: number;
  max?: number;
  label: string;
  icon: React.ReactNode;
  unit?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
}

function GaugeBar({
  value,
  max = 100,
  label,
  icon,
  unit = '%',
  warningThreshold = 70,
  criticalThreshold = 90,
}: GaugeBarProps) {
  const pct = Math.min((value / max) * 100, 100);

  const barColor =
    pct >= criticalThreshold
      ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'
      : pct >= warningThreshold
        ? 'bg-yellow-500'
        : 'bg-green-500';

  const textColor =
    pct >= criticalThreshold
      ? 'text-red-500'
      : pct >= warningThreshold
        ? 'text-yellow-500'
        : 'text-foreground';

  return (
    <div className="flex items-center gap-2">
      <div className="text-muted-foreground">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center mb-0.5">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</span>
          <span className={cn('text-[10px] font-bold font-mono', textColor)}>
            {value.toFixed(0)}{unit}
          </span>
        </div>
        <div className="h-1.5 bg-muted/30 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-500', barColor)}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ── Sparkline color from threshold ──────────────────────────────────────────
function sparkColor(value: number, warn: number, crit: number): string {
  if (value >= crit) return '#ef4444';
  if (value >= warn) return '#eab308';
  return 'hsl(var(--primary))';
}

// ── Main component ───────────────────────────────────────────────────────────

interface SystemResourcesSectionProps {
  className?: string;
}

export function SystemResourcesSection({ className }: SystemResourcesSectionProps) {
  const { isConnected } = useRos();
  const status = useSystemStatus();

  const cpuData  = useTimeSeriesBuffer(status?.cpu_percent,  { maxAge: 60 });
  const ramData  = useTimeSeriesBuffer(status?.ram_percent,  { maxAge: 60 });
  const tempData = useTimeSeriesBuffer(status?.cpu_temp,     { maxAge: 60 });

  const offlineBadge = (!isConnected || !status) ? (
    <span className="text-[10px] text-muted-foreground ml-auto mr-1">
      {!isConnected ? 'Offline' : 'Waiting…'}
    </span>
  ) : undefined;

  return (
    <SectionHeader
      icon={Activity}
      title="System"
      badge={offlineBadge}
      defaultOpen
      className={className}
    >
      {isConnected && status ? (
        <div className="space-y-2.5">
          {/* CPU */}
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <GaugeBar
                value={status.cpu_percent}
                label="CPU"
                icon={<Cpu className="w-3 h-3" />}
                warningThreshold={70}
                criticalThreshold={90}
              />
            </div>
            <Sparkline
              data={cpuData}
              width={64}
              height={20}
              color={sparkColor(status.cpu_percent, 70, 90)}
            />
          </div>

          {/* RAM */}
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <GaugeBar
                value={status.ram_percent}
                label="RAM"
                icon={<Activity className="w-3 h-3" />}
                warningThreshold={80}
                criticalThreshold={95}
              />
            </div>
            <Sparkline
              data={ramData}
              width={64}
              height={20}
              color={sparkColor(status.ram_percent, 80, 95)}
            />
          </div>

          {/* Temperature */}
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <GaugeBar
                value={status.cpu_temp}
                max={100}
                label="Temp"
                icon={<Thermometer className="w-3 h-3" />}
                unit="°"
                warningThreshold={70}
                criticalThreshold={85}
              />
            </div>
            <Sparkline
              data={tempData}
              width={64}
              height={20}
              color={sparkColor(status.cpu_temp, 70, 85)}
            />
          </div>

          {/* Disk — no sparkline, changes too slowly */}
          <GaugeBar
            value={status.disk_percent}
            label="Disk"
            icon={<HardDrive className="w-3 h-3" />}
            warningThreshold={85}
            criticalThreshold={95}
          />
        </div>
      ) : (
        <div className="text-[10px] text-muted-foreground py-1">
          {!isConnected ? 'Connect rosbridge to see system metrics.' : 'Waiting for system_status_enriched…'}
        </div>
      )}
    </SectionHeader>
  );
}
