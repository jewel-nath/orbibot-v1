/**
 * BatteryChart - Voltage over time with threshold lines.
 */

import { useBattery } from '@/hooks/useBattery';
import { useTimeSeriesBuffer } from '@/hooks/useTimeSeriesBuffer';
import { TimeSeriesChart } from './charts/TimeSeriesChart';
import { BATTERY_PARAMS } from '@/lib/constants';

export function BatteryChart() {
  const battery = useBattery();
  const voltage = battery?.voltage ?? null;
  const history = useTimeSeriesBuffer(voltage, { maxAge: 300, sampleInterval: 1000 });

  const channels = [
    { name: 'Voltage', color: 'hsl(var(--primary))', data: history },
  ];

  const thresholds = [
    { value: BATTERY_PARAMS.full, color: '#22C55E', label: `Full (${BATTERY_PARAMS.full}V)` },
    { value: BATTERY_PARAMS.lowThreshold, color: '#EAB308', label: `Low (${BATTERY_PARAMS.lowThreshold}V)` },
    { value: BATTERY_PARAMS.criticalThreshold, color: '#EF4444', label: `Critical (${BATTERY_PARAMS.criticalThreshold}V)` },
  ];

  // Compute discharge rate from history
  let dischargeRate: string | null = null;
  if (history.length >= 10) {
    const first = history[0];
    const last = history[history.length - 1];
    const dt = (last.t - first.t) / 60000; // minutes
    if (dt > 0.1) {
      const rate = (last.value - first.value) / dt;
      dischargeRate = `${rate >= 0 ? '+' : ''}${rate.toFixed(3)} V/min`;
    }
  }

  return (
    <div className="space-y-2">
      {dischargeRate && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Discharge rate:</span>
          <span className="font-mono font-medium">{dischargeRate}</span>
        </div>
      )}
      <TimeSeriesChart
        channels={channels}
        thresholds={thresholds}
        height={200}
        yLabel="Volts"
        yMin={10}
        yMax={15}
        timeWindow={300}
        showLegend={false}
      />
    </div>
  );
}
