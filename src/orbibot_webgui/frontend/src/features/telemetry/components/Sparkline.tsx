/**
 * Sparkline - Minimal inline SVG time-series line chart using D3.
 * No axes, no labels — just the trend line with optional gradient fill.
 * Designed for tight 80×24px inline use alongside gauge bars.
 */

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import type { TimeSeriesPoint } from '@/hooks/useTimeSeriesBuffer';

interface SparklineProps {
  data: TimeSeriesPoint[];
  width?: number;
  height?: number;
  /** CSS color string — defaults to hsl(var(--primary)) */
  color?: string;
  fillOpacity?: number;
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  color,
  fillOpacity = 0.15,
  className,
}: SparklineProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (!svgRef.current || data.length < 2) return;

    const m = { top: 2, right: 1, bottom: 2, left: 1 };
    const w = width - m.left - m.right;
    const h = height - m.top - m.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${m.left},${m.top})`);

    const xScale = d3
      .scaleLinear()
      .domain([data[0].t, data[data.length - 1].t])
      .range([0, w]);

    const vals = data.map(d => d.value);
    const minV = Math.min(...vals);
    const maxV = Math.max(...vals);
    const span = maxV - minV;
    const pad = span === 0 ? 1 : span * 0.12;

    const yScale = d3
      .scaleLinear()
      .domain([minV - pad, maxV + pad])
      .range([h, 0]);

    const curve = d3.curveCatmullRom.alpha(0.5);

    const lineGen = d3
      .line<TimeSeriesPoint>()
      .x(d => xScale(d.t))
      .y(d => yScale(d.value))
      .curve(curve);

    const areaGen = d3
      .area<TimeSeriesPoint>()
      .x(d => xScale(d.t))
      .y0(h)
      .y1(d => yScale(d.value))
      .curve(curve);

    const stroke = color ?? 'hsl(var(--primary))';

    g.append('path')
      .datum(data)
      .attr('d', areaGen)
      .attr('fill', stroke)
      .attr('fill-opacity', fillOpacity);

    g.append('path')
      .datum(data)
      .attr('d', lineGen)
      .attr('fill', 'none')
      .attr('stroke', stroke)
      .attr('stroke-width', 1.5)
      .attr('stroke-linecap', 'round')
      .attr('stroke-linejoin', 'round');
  }, [data, width, height, color, fillOpacity]);

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      className={cn('shrink-0', data.length < 2 && 'opacity-25', className)}
    />
  );
}
