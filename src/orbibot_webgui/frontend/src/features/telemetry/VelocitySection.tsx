/**
 * VelocitySection - Collapsible velocity display with directional arrow.
 * Left: VelocityArrow SVG — direction and magnitude of vx/vy + rotation wz.
 * Right: Vx / Vy / Wz numeric values, highlighted when non-zero.
 * Bottom: speed magnitude + sparkline trend.
 */

import { useOdometry } from '@/hooks/useOdometry';
import { useRos } from '@/contexts/RosContext';
import { useTimeSeriesBuffer } from '@/hooks/useTimeSeriesBuffer';
import { SectionHeader, VelocityArrow, Sparkline } from './components';
import { cn } from '@/lib/utils';
import { Gauge } from 'lucide-react';

interface VelocitySectionProps {
  className?: string;
}

export function VelocitySection({ className }: VelocitySectionProps) {
  const { isConnected } = useRos();
  const odom = useOdometry();

  const vx = odom?.vx ?? 0;
  const vy = odom?.vy ?? 0;
  const wz = odom?.vtheta ?? 0;
  const speed = Math.sqrt(vx * vx + vy * vy);

  const speedData = useTimeSeriesBuffer(odom ? speed : null, { maxAge: 60 });

  const isActive = (v: number) => Math.abs(v) > 0.01;

  return (
    <SectionHeader
      icon={Gauge}
      title="Velocity"
      defaultOpen
      className={className}
    >
      {!isConnected || !odom ? (
        <div className="text-[10px] text-muted-foreground py-1">
          {!isConnected ? 'Offline' : 'Waiting for odometry…'}
        </div>
      ) : (
        <div className="space-y-2.5">
          {/* Arrow + values row */}
          <div className="flex items-center gap-3">
            <VelocityArrow vx={vx} vy={vy} wz={wz} size={76} />

            {/* Vx / Vy / Wz values */}
            <div className="flex-1 min-w-0 space-y-1.5">
              {[
                { label: 'Vx', value: vx, unit: 'm/s' },
                { label: 'Vy', value: vy, unit: 'm/s' },
                { label: 'Wz', value: wz, unit: 'r/s' },
              ].map(({ label, value, unit }) => (
                <div key={label} className="flex items-baseline justify-between gap-1">
                  <span className="text-[10px] text-muted-foreground w-6 shrink-0">{label}</span>
                  <span className={cn(
                    'font-mono text-xs font-semibold',
                    isActive(value) ? 'text-primary' : 'text-foreground'
                  )}>
                    {value.toFixed(2)}
                    <span className="text-[9px] text-muted-foreground ml-0.5">{unit}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Speed + sparkline */}
          <div className="flex items-center gap-2 pt-1.5 border-t border-border/40">
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-1">
                <span className="text-[10px] text-muted-foreground">Speed</span>
                <span className={cn(
                  'font-mono text-xs font-bold ml-1',
                  isActive(speed) ? 'text-primary' : 'text-foreground'
                )}>
                  {speed.toFixed(3)}
                  <span className="text-[9px] text-muted-foreground ml-0.5">m/s</span>
                </span>
              </div>
            </div>
            <Sparkline data={speedData} width={72} height={20} />
          </div>
        </div>
      )}
    </SectionHeader>
  );
}
