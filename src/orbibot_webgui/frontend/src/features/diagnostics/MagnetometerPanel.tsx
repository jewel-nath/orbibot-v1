/**
 * MagnetometerPanel - Scatter plot of mag_x vs mag_y to visualize calibration quality.
 */

import { useEffect, useRef, useState } from 'react';
import { useMagnetometer } from '@/hooks/useMagnetometer';
import { ScatterPlot, type CircleOverlay } from './charts/ScatterPlot';

const MAX_POINTS = 1000;
const SAMPLE_INTERVAL_MS = 100;

export function MagnetometerPanel() {
  const mag = useMagnetometer();
  const bufferRef = useRef<{ x: number; y: number }[]>([]);
  const lastSampleRef = useRef(0);
  const [, setVersion] = useState(0);

  useEffect(() => {
    if (!mag) return;
    const now = Date.now();
    if (now - lastSampleRef.current < SAMPLE_INTERVAL_MS) return;
    lastSampleRef.current = now;

    bufferRef.current.push({ x: mag.x, y: mag.y });
    if (bufferRef.current.length > MAX_POINTS) {
      bufferRef.current = bufferRef.current.slice(-MAX_POINTS);
    }
    setVersion(v => v + 1);
  }, [mag]);

  const points = bufferRef.current;

  // Compute center (mean) for circle overlay
  let overlay: CircleOverlay | undefined;
  if (points.length >= 20) {
    const cx = points.reduce((s, p) => s + p.x, 0) / points.length;
    const cy = points.reduce((s, p) => s + p.y, 0) / points.length;
    const r = Math.sqrt(
      points.reduce((s, p) => s + (p.x - cx) ** 2 + (p.y - cy) ** 2, 0) / points.length
    );
    overlay = { cx, cy, r, color: '#F59E0B', label: `Center: (${cx.toFixed(1)}, ${cy.toFixed(1)})` };
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="font-mono">{points.length} samples</span>
        {mag && (
          <span className="font-mono">
            X={mag.x.toFixed(1)} Y={mag.y.toFixed(1)} Z={mag.z.toFixed(1)}
          </span>
        )}
        {overlay && (
          <span className="font-mono text-amber-500">
            Offset: ({overlay.cx.toFixed(1)}, {overlay.cy.toFixed(1)})
          </span>
        )}
      </div>
      <ScatterPlot
        points={points}
        pointColor="hsl(var(--primary))"
        overlays={overlay ? [overlay] : undefined}
        xLabel="Mag X"
        yLabel="Mag Y"
        height={320}
        lockAspect
      />
      <p className="text-[10px] text-muted-foreground">
        A well-calibrated magnetometer shows points centered at (0,0). The yellow circle shows the estimated offset (hard-iron error).
      </p>
    </div>
  );
}
