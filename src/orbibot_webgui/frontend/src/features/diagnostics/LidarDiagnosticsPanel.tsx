/**
 * LidarDiagnosticsPanel - LiDAR polar view with scan statistics.
 */

import { useMemo } from 'react';
import { LidarView } from '@/components/visualization/LidarView';
import { useLidarScan } from '@/hooks/useLidarScan';

export function LidarDiagnosticsPanel() {
  const scan = useLidarScan();

  const stats = useMemo(() => {
    if (!scan?.ranges?.length) return null;
    const valid = scan.ranges.filter(r => Number.isFinite(r) && r > scan.range_min && r < scan.range_max);
    if (valid.length === 0) return null;
    return {
      count: scan.ranges.length,
      validCount: valid.length,
      min: Math.min(...valid),
      max: Math.max(...valid),
      mean: valid.reduce((a, b) => a + b, 0) / valid.length,
      scanHz: scan.scan_time > 0 ? (1 / scan.scan_time).toFixed(1) : '—',
    };
  }, [scan]);

  return (
    <div className="space-y-3">
      <LidarView maxRange={6} />

      {stats ? (
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Readings', value: `${stats.validCount}/${stats.count}` },
            { label: 'Min Range', value: `${stats.min.toFixed(2)} m` },
            { label: 'Max Range', value: `${stats.max.toFixed(2)} m` },
            { label: 'Mean Range', value: `${stats.mean.toFixed(2)} m` },
            { label: 'Scan Rate', value: `${stats.scanHz} Hz` },
            { label: 'FOV', value: scan ? `${((scan.angle_max - scan.angle_min) * 180 / Math.PI).toFixed(0)}°` : '—' },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</div>
              <div className="font-mono text-xs font-medium">{value}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground text-center">No LiDAR data available.</p>
      )}
    </div>
  );
}
