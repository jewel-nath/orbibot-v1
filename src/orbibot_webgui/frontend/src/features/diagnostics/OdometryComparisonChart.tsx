/**
 * OdometryComparisonChart - Raw vs filtered odometry velocity time-series.
 */

import { useState } from 'react';
import { useOdometry } from '@/hooks/useOdometry';
import { useSubscriber } from '@/hooks/useSubscriber';
import { useMultiChannelTimeSeries } from '@/hooks/useMultiChannelTimeSeries';
import { TimeSeriesChart } from './charts/TimeSeriesChart';
import { ROS_MESSAGE_TYPES } from '@/lib/constants';
import type { Odometry } from '@/types/ros';

const TIME_WINDOWS = [10, 30, 60] as const;

export function OdometryComparisonChart() {
  const [timeWindow, setTimeWindow] = useState<number>(30);

  // Raw odom velocities
  const { data: rawOdom } = useSubscriber<Odometry>({
    topic: '/odom',
    messageType: ROS_MESSAGE_TYPES.odometry,
    throttleRate: 100,
  });

  // Filtered odom velocities (useOdometry subscribes to the configured topic)
  const filteredOdom = useOdometry();

  const velocities: Record<string, number | null> = {
    'Raw Vx': rawOdom?.twist?.twist?.linear?.x ?? null,
    'Filtered Vx': filteredOdom?.vx ?? null,
    'Raw Vy': rawOdom?.twist?.twist?.linear?.y ?? null,
    'Filtered Vy': filteredOdom?.vy ?? null,
    'Raw Wz': rawOdom?.twist?.twist?.angular?.z ?? null,
    'Filtered Wz': filteredOdom?.vtheta ?? null,
  };

  const history = useMultiChannelTimeSeries(velocities, { maxAge: 60, sampleInterval: 100 });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Time window:</span>
        {TIME_WINDOWS.map(w => (
          <button
            key={w}
            onClick={() => setTimeWindow(w)}
            className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
              timeWindow === w
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {w}s
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <div className="rounded-lg border border-border bg-muted/10 p-3">
          <div className="text-xs font-semibold text-muted-foreground mb-2">Vx — Forward/Back (m/s)</div>
          <TimeSeriesChart
            channels={[
              { name: 'Raw', color: '#6DB4FF', data: history['Raw Vx'] ?? [], dashed: true },
              { name: 'Filtered', color: '#22C55E', data: history['Filtered Vx'] ?? [] },
            ]}
            height={180}
            timeWindow={timeWindow}
            showLegend
          />
        </div>
        <div className="rounded-lg border border-border bg-muted/10 p-3">
          <div className="text-xs font-semibold text-muted-foreground mb-2">Vy — Strafe (m/s)</div>
          <TimeSeriesChart
            channels={[
              { name: 'Raw', color: '#6DB4FF', data: history['Raw Vy'] ?? [], dashed: true },
              { name: 'Filtered', color: '#22C55E', data: history['Filtered Vy'] ?? [] },
            ]}
            height={180}
            timeWindow={timeWindow}
            showLegend
          />
        </div>
        <div className="rounded-lg border border-border bg-muted/10 p-3 md:col-span-2 xl:col-span-1">
          <div className="text-xs font-semibold text-muted-foreground mb-2">Wz — Rotation (rad/s)</div>
          <TimeSeriesChart
            channels={[
              { name: 'Raw', color: '#6DB4FF', data: history['Raw Wz'] ?? [], dashed: true },
              { name: 'Filtered', color: '#22C55E', data: history['Filtered Wz'] ?? [] },
            ]}
            height={180}
            timeWindow={timeWindow}
            showLegend
          />
        </div>
      </div>
    </div>
  );
}
