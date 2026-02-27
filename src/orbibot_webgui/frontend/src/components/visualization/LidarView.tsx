/**
 * LidarView - 2D polar plot visualization for LiDAR scans
 */

import { useEffect, useRef } from 'react';
import { useLidarScan } from '@/hooks/useLidarScan';
import { cn } from '@/lib/utils';
import { Radar } from 'lucide-react';
import * as d3 from 'd3';

interface LidarViewProps {
  className?: string;
  maxRange?: number; // Maximum range to display (meters)
  compact?: boolean;
}

/**
 * LidarView component
 * Displays real-time LiDAR scan data as a polar plot using D3.js
 * - 360° polar coordinate visualization
 * - Range: 0-12m (configurable)
 * - Real-time updates @ 10Hz
 */
export function LidarView({ className, maxRange = 12, compact = false }: LidarViewProps) {
  const scan = useLidarScan();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // D3 visualization
  useEffect(() => {
    if (!svgRef.current || !containerRef.current || !scan) return;

    const container = containerRef.current;
    const svg = d3.select(svgRef.current);

    // Get container dimensions
    const width = container.clientWidth;
    const height = container.clientHeight;
    const centerX = width / 2;
    const centerY = height / 2;
    const margin = compact ? 10 : 40;
    const radius = Math.min(width, height) / 2 - margin;

    // Clear previous render
    svg.selectAll('*').remove();

    // Set SVG dimensions
    svg.attr('width', width).attr('height', height);

    // Create main group
    const g = svg.append('g').attr('transform', `translate(${centerX},${centerY})`);

    // Scale for radius (distance)
    const radiusScale = d3.scaleLinear().domain([0, maxRange]).range([0, radius]);

    // Draw concentric circles (range rings)
    const rangeRings = [3, 6, 9, 12]; // meters
    rangeRings.forEach((range) => {
      if (range <= maxRange) {
        g.append('circle')
          .attr('r', radiusScale(range))
          .attr('fill', 'none')
          .attr('stroke', 'currentColor')
          .attr('stroke-width', 1)
          .attr('stroke-opacity', 0.2)
          .attr('class', 'text-muted-foreground');

        // Range labels (skip in compact mode)
        if (!compact) {
          g.append('text')
            .attr('x', 0)
            .attr('y', -radiusScale(range) - 5)
            .attr('text-anchor', 'middle')
            .attr('font-size', '10px')
            .attr('fill', 'currentColor')
            .attr('opacity', 0.5)
            .attr('class', 'text-muted-foreground')
            .text(`${range}m`);
        }
      }
    });

    // Draw cardinal direction lines
    const directions = [
      { angle: 0, label: 'N' },
      { angle: 90, label: 'E' },
      { angle: 180, label: 'S' },
      { angle: 270, label: 'W' },
    ];

    directions.forEach(({ angle, label }) => {
      const rad = (angle * Math.PI) / 180;
      const x = radius * Math.cos(rad - Math.PI / 2);
      const y = radius * Math.sin(rad - Math.PI / 2);

      g.append('line')
        .attr('x1', 0)
        .attr('y1', 0)
        .attr('x2', x)
        .attr('y2', y)
        .attr('stroke', 'currentColor')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', 0.2)
        .attr('class', 'text-muted-foreground');

      if (!compact) {
        g.append('text')
          .attr('x', x * 1.1)
          .attr('y', y * 1.1)
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'middle')
          .attr('font-size', '12px')
          .attr('font-weight', 'bold')
          .attr('fill', 'currentColor')
          .attr('class', 'text-muted-foreground')
          .text(label);
      }
    });

    // Plot scan points
    const { angle_min, angle_increment, ranges } = scan;

    // Convert scan data to polar coordinates
    const scanPoints = ranges
      .map((range, i) => {
        const angle = angle_min + i * angle_increment;
        return {
          angle,
          range,
          valid: range > scan.range_min && range < scan.range_max && isFinite(range),
        };
      })
      .filter((point) => point.valid && point.range <= maxRange);

    // Draw scan points as a path
    if (scanPoints.length > 0) {
      const lineGenerator = d3
        .lineRadial<{ angle: number; range: number }>()
        .angle((d) => -d.angle) // Negate to match RViz (flip left/right)
        .radius((d) => radiusScale(d.range))
        .curve(d3.curveLinearClosed);

      g.append('path')
        .datum(scanPoints)
        .attr('d', lineGenerator)
        .attr('fill', 'currentColor')
        .attr('fill-opacity', 0.1)
        .attr('stroke', 'currentColor')
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 0.8)
        .attr('class', 'text-primary');

      // Draw individual scan points
      g.selectAll('circle.scan-point')
        .data(scanPoints)
        .enter()
        .append('circle')
        .attr('class', 'scan-point')
        .attr('cx', (d) => radiusScale(d.range) * Math.cos(-d.angle - Math.PI / 2))
        .attr('cy', (d) => radiusScale(d.range) * Math.sin(-d.angle - Math.PI / 2))
        .attr('r', 2)
        .attr('fill', 'currentColor')
        .attr('class', 'text-primary');
    }

    // Robot position indicator (center)
    g.append('circle')
      .attr('r', 5)
      .attr('fill', 'currentColor')
      .attr('class', 'text-green-500');

    g.append('circle')
      .attr('r', 3)
      .attr('fill', 'white');
  }, [scan, maxRange, compact]);

  // Loading state
  if (!scan) {
    return (
      <div className={cn(compact ? 'p-3' : 'p-6', 'bg-card rounded-lg border', className)}>
        <div className="flex items-center gap-3 mb-2">
          <Radar className="w-5 h-5 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-muted-foreground">LiDAR</h3>
        </div>
        <div className="text-muted-foreground text-xs">Waiting for scan data...</div>
        {!compact && (
          <div className="text-[10px] text-muted-foreground/60 mt-4 bg-black/20 px-2 py-1 rounded font-mono inline-block">
            ros2 launch orbibot_bringup lidar.launch.py
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={cn(compact ? 'p-2' : 'p-6', 'bg-card rounded-lg border', className)}>
      {/* Header */}
      {!compact && (
        <div className="flex items-center gap-3 mb-3">
          <Radar className="w-5 h-5 text-muted-foreground" />
          <h3 className="text-sm font-semibold">LiDAR</h3>
        </div>
      )}

      {/* Polar Plot */}
      <div
        ref={containerRef}
        className="relative bg-muted/20 rounded-lg overflow-hidden"
        style={{ aspectRatio: '1/1' }}
      >
        <svg ref={svgRef} className="w-full h-full" />
      </div>

      {/* Detailed scan stats removed for a cleaner expanded view */}
    </div>
  );
}
