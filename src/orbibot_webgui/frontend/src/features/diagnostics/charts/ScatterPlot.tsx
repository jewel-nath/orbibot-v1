/**
 * ScatterPlot - Reusable D3 2D scatter/path plot.
 *
 * Used for magnetometer XY scatter and odometry path trace.
 * Features: aspect ratio lock, pan/zoom, paths with optional dashing, grid lines.
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';

export interface ScatterPath {
  name: string;
  color: string;
  points: { x: number; y: number }[];
  dashed?: boolean;
  showDots?: boolean;
}

export interface CircleOverlay {
  cx: number;
  cy: number;
  r: number;
  color: string;
  label?: string;
}

interface ScatterPlotProps {
  paths?: ScatterPath[];
  points?: { x: number; y: number }[];
  pointColor?: string;
  xLabel?: string;
  yLabel?: string;
  height?: number;
  lockAspect?: boolean;
  gridSpacing?: number;
  overlays?: CircleOverlay[];
  robotMarker?: { x: number; y: number; yaw: number };
  className?: string;
}

export function ScatterPlot({
  paths,
  points,
  pointColor = 'hsl(var(--primary))',
  xLabel,
  yLabel,
  height = 400,
  lockAspect = true,
  gridSpacing,
  overlays,
  robotMarker,
  className,
}: ScatterPlotProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setContainerWidth(el.clientWidth);
    const ro = new ResizeObserver(update);
    ro.observe(el);
    update();
    const t = setTimeout(update, 50);
    return () => { clearTimeout(t); ro.disconnect(); };
  }, []);

  const drawWidth = Math.max(containerWidth, 280);

  useEffect(() => {
    if (!svgRef.current || drawWidth < 100) return;

    try {
      const width = drawWidth;
      const margin = { top: 12, right: 14, bottom: 32, left: 48 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();
      svg.attr('width', width).attr('height', height);

      // Collect all points
      const allPoints = [
        ...(points ?? []),
        ...(paths?.flatMap(p => p.points) ?? []),
      ];

      if (allPoints.length === 0) {
        svg.append('text')
          .attr('x', width / 2).attr('y', height / 2)
          .attr('text-anchor', 'middle')
          .attr('font-size', '12px')
          .attr('fill', 'currentColor')
          .attr('opacity', 0.5)
          .text('No data');
        return;
      }

      let xMin = Math.min(...allPoints.map(p => p.x));
      let xMax = Math.max(...allPoints.map(p => p.x));
      let yMin = Math.min(...allPoints.map(p => p.y));
      let yMax = Math.max(...allPoints.map(p => p.y));

      // Add padding
      const xSpan = xMax - xMin || 1;
      const ySpan = yMax - yMin || 1;
      const pad = 0.15;
      xMin -= xSpan * pad; xMax += xSpan * pad;
      yMin -= ySpan * pad; yMax += ySpan * pad;

      // Lock aspect ratio
      if (lockAspect) {
        const xRange = xMax - xMin;
        const yRange = yMax - yMin;
        const aspect = innerWidth / innerHeight;
        if (xRange / yRange > aspect) {
          const mid = (yMin + yMax) / 2;
          const half = (xRange / aspect) / 2;
          yMin = mid - half; yMax = mid + half;
        } else {
          const mid = (xMin + xMax) / 2;
          const half = (yRange * aspect) / 2;
          xMin = mid - half; xMax = mid + half;
        }
      }

      const xScale = d3.scaleLinear().domain([xMin, xMax]).range([0, innerWidth]);
      const yScale = d3.scaleLinear().domain([yMin, yMax]).range([innerHeight, 0]);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      // Grid
      if (gridSpacing) {
        const xStart = Math.ceil(xMin / gridSpacing) * gridSpacing;
        const yStart = Math.ceil(yMin / gridSpacing) * gridSpacing;
        for (let x = xStart; x <= xMax; x += gridSpacing) {
          g.append('line')
            .attr('x1', xScale(x)).attr('x2', xScale(x))
            .attr('y1', 0).attr('y2', innerHeight)
            .attr('stroke', 'currentColor').attr('stroke-opacity', 0.08);
        }
        for (let y = yStart; y <= yMax; y += gridSpacing) {
          g.append('line')
            .attr('x1', 0).attr('x2', innerWidth)
            .attr('y1', yScale(y)).attr('y2', yScale(y))
            .attr('stroke', 'currentColor').attr('stroke-opacity', 0.08);
        }
      }

      // Circle overlays
      if (overlays) {
        for (const ov of overlays) {
          const cx = xScale(ov.cx);
          const cy = yScale(ov.cy);
          const rx = Math.abs(xScale(ov.cx + ov.r) - xScale(ov.cx));
          g.append('circle')
            .attr('cx', cx).attr('cy', cy).attr('r', rx)
            .attr('fill', 'none')
            .attr('stroke', ov.color)
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '4,3')
            .attr('opacity', 0.6);
          if (ov.label) {
            g.append('text')
              .attr('x', cx).attr('y', cy - rx - 6)
              .attr('text-anchor', 'middle')
              .attr('font-size', '10px')
              .attr('fill', ov.color)
              .attr('opacity', 0.7)
              .text(ov.label);
          }
        }
      }

      // Scatter points
      if (points && points.length > 0) {
        g.selectAll('.dot')
          .data(points)
          .enter()
          .append('circle')
          .attr('cx', d => xScale(d.x))
          .attr('cy', d => yScale(d.y))
          .attr('r', 2)
          .attr('fill', pointColor)
          .attr('opacity', 0.6);
      }

      // Paths
      if (paths) {
        const lineGen = d3.line<{ x: number; y: number }>()
          .x(d => xScale(d.x))
          .y(d => yScale(d.y))
          .defined(d => Number.isFinite(d.x) && Number.isFinite(d.y));

        for (const path of paths) {
          if (path.points.length < 2) continue;
          const pathD = lineGen(path.points);
          if (!pathD) continue;
          const el = g.append('path')
            .attr('d', pathD)
            .attr('fill', 'none')
            .attr('stroke', path.color)
            .attr('stroke-width', 2);
          if (path.dashed) el.attr('stroke-dasharray', '5,4');

          if (path.showDots) {
            g.selectAll(`.dot-${path.name}`)
              .data(path.points)
              .enter()
              .append('circle')
              .attr('cx', d => xScale(d.x))
              .attr('cy', d => yScale(d.y))
              .attr('r', 1.5)
              .attr('fill', path.color)
              .attr('opacity', 0.4);
          }
        }
      }

      // Robot marker (oriented triangle)
      if (robotMarker) {
        const rx = xScale(robotMarker.x);
        const ry = yScale(robotMarker.y);
        const size = 10;
        const angle = -robotMarker.yaw; // screen coords
        const tri = d3.symbol().type(d3.symbolTriangle).size(size * size);
        g.append('path')
          .attr('d', tri)
          .attr('transform', `translate(${rx},${ry}) rotate(${(angle * 180) / Math.PI - 90})`)
          .attr('fill', 'hsl(var(--primary))')
          .attr('stroke', 'hsl(var(--background))')
          .attr('stroke-width', 1.5);
      }

      // Axes
      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(xScale).ticks(6))
        .attr('font-size', '10px')
        .attr('color', 'currentColor');
      g.append('g')
        .call(d3.axisLeft(yScale).ticks(6))
        .attr('font-size', '10px')
        .attr('color', 'currentColor');

      // Labels
      if (xLabel) {
        svg.append('text')
          .attr('x', margin.left + innerWidth / 2)
          .attr('y', height - 4)
          .attr('text-anchor', 'middle')
          .attr('font-size', '10px')
          .attr('fill', 'currentColor')
          .attr('opacity', 0.6)
          .text(xLabel);
      }
      if (yLabel) {
        svg.append('text')
          .attr('transform', `translate(12,${margin.top + innerHeight / 2}) rotate(-90)`)
          .attr('text-anchor', 'middle')
          .attr('font-size', '10px')
          .attr('fill', 'currentColor')
          .attr('opacity', 0.6)
          .text(yLabel);
      }
    } catch (err) {
      console.error('ScatterPlot render error:', err);
    }
  }, [paths, points, pointColor, xLabel, yLabel, height, lockAspect, gridSpacing, overlays, robotMarker, drawWidth]);

  return (
    <div ref={containerRef} className={cn('w-full min-w-[280px]', className)} style={{ minHeight: height }}>
      <svg ref={svgRef} className="overflow-visible block" width={drawWidth} height={height} />
    </div>
  );
}
