/**
 * OdometryPathTrace - 2D XY path visualization showing raw vs filtered odometry.
 */

import { useOdometryPath } from '@/hooks/useOdometryPath';
import { ScatterPlot } from './charts/ScatterPlot';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';

export function OdometryPathTrace() {
  const { rawPath, filteredPath, currentFiltered, clear } = useOdometryPath();

  const paths = [
    {
      name: 'Raw (/odom)',
      color: '#6DB4FF',
      points: rawPath.map(p => ({ x: p.x, y: p.y })),
      dashed: true,
    },
    {
      name: 'Filtered (/odometry/filtered)',
      color: '#22C55E',
      points: filteredPath.map(p => ({ x: p.x, y: p.y })),
    },
  ];

  const hasData = rawPath.length > 0 || filteredPath.length > 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5 border-t-2 border-dashed" style={{ borderColor: '#6DB4FF' }} />
            Raw
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5 bg-green-500" />
            Filtered
          </span>
          <span className="font-mono">
            {rawPath.length} / {filteredPath.length} pts
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={clear}
          disabled={!hasData}
          className="gap-1.5 h-7"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Clear
        </Button>
      </div>

      <ScatterPlot
        paths={paths}
        height={420}
        lockAspect
        gridSpacing={0.5}
        xLabel="X (m)"
        yLabel="Y (m)"
        robotMarker={currentFiltered ? { x: currentFiltered.x, y: currentFiltered.y, yaw: currentFiltered.yaw } : undefined}
      />
    </div>
  );
}
