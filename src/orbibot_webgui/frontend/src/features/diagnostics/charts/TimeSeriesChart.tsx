/**
 * TimeSeriesChart - Reusable multi-channel D3 time-series line chart.
 *
 * Generalizes the LineChart pattern from PIDResponseGraph for any number of channels.
 * Features: auto-scaling Y, configurable time window, threshold lines, legend, hover tooltip.
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import { type TimeSeriesPoint } from '@/hooks/useTimeSeriesBuffer';

const CHART_HEIGHT_DEFAULT = 220;
const CHART_MIN_WIDTH = 280;
const CHART_FALLBACK_WIDTH = 400;
const MIN_Y_SPAN_DEFAULT = 0.01;

export interface ChartChannel {
  name: string;
  color: string;
  data: TimeSeriesPoint[];
  dashed?: boolean;
}

export interface ChartThreshold {
  value: number;
  color: string;
  label?: string;
}

interface TimeSeriesChartProps {
  channels: ChartChannel[];
  height?: number;
  yLabel?: string;
  yMin?: number;
  yMax?: number;
  minYSpan?: number;
  showLegend?: boolean;
  thresholds?: ChartThreshold[];
  timeWindow?: number; // seconds of visible window (default: auto from data)
  className?: string;
}

function domainWithMinSpan(lo: number, hi: number, minSpan: number): [number, number] {
  const safeLo = Number.isFinite(lo) ? lo : 0;
  const safeHi = Number.isFinite(hi) ? hi : 1;
  const span = safeHi - safeLo;
  if (!Number.isFinite(span) || span < minSpan) {
    const half = minSpan / 2;
    const mid = (safeLo + safeHi) / 2;
    return [mid - half, mid + half];
  }
  const padding = span * 0.1 || 0.05;
  return [safeLo - padding, safeHi + padding];
}

function formatValue(v: number): string {
  const x = Number.isFinite(v) ? v : 0;
  const abs = Math.abs(x);
  if (abs >= 100) return x.toFixed(1);
  if (abs >= 1) return x.toFixed(2);
  if (abs >= 0.01) return x.toFixed(3);
  if (abs >= 0.001) return x.toFixed(4);
  return x.toExponential(1);
}

export function TimeSeriesChart({
  channels,
  height = CHART_HEIGHT_DEFAULT,
  yLabel,
  yMin,
  yMax,
  minYSpan = MIN_Y_SPAN_DEFAULT,
  showLegend = true,
  thresholds,
  timeWindow,
  className,
}: TimeSeriesChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; values: { name: string; color: string; value: number }[]; time: string } | null>(null);

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

  const drawWidth = containerWidth >= CHART_MIN_WIDTH ? containerWidth : CHART_FALLBACK_WIDTH;

  useEffect(() => {
    if (!svgRef.current) return;

    try {
      const width = drawWidth;
      const margin = { top: 12, right: 14, bottom: 28, left: 52 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();
      svg.attr('width', width).attr('height', height);

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

      // Compute time domain
      const now = Date.now();
      let tMin: number, tMax: number;
      if (timeWindow) {
        tMax = now;
        tMin = now - timeWindow * 1000;
      } else {
        const allTimes = channels.flatMap(c => c.data.map(d => d.t));
        tMin = allTimes.length ? Math.min(...allTimes) : now - 60000;
        tMax = allTimes.length ? Math.max(...allTimes) : now;
        if (tMax - tMin < 1000) tMax = tMin + 1000;
      }

      // Compute Y domain
      const allValues = channels.flatMap(c => c.data.map(d => d.value).filter(Number.isFinite));
      const thresholdValues = thresholds?.map(t => t.value).filter(Number.isFinite) ?? [];
      const allYVals = [...allValues, ...thresholdValues];

      let computedYMin = allYVals.length ? Math.min(...allYVals) : 0;
      let computedYMax = allYVals.length ? Math.max(...allYVals) : 1;
      if (yMin !== undefined) computedYMin = yMin;
      if (yMax !== undefined) computedYMax = yMax;
      const [domainLo, domainHi] = domainWithMinSpan(computedYMin, computedYMax, minYSpan);

      const xScale = d3.scaleLinear().domain([tMin, tMax]).range([0, innerWidth]);
      const yScale = d3.scaleLinear().domain([domainLo, domainHi]).range([innerHeight, 0]);

      // Grid
      const xAxisGrid = d3.axisBottom(xScale).ticks(6).tickSize(-innerHeight).tickFormat(() => '');
      const yAxisGrid = d3.axisLeft(yScale).ticks(5).tickSize(-innerWidth).tickFormat(() => '');

      g.append('g').attr('transform', `translate(0,${innerHeight})`).call(xAxisGrid)
        .selectAll('line').attr('stroke-opacity', 0.1);
      g.append('g').call(yAxisGrid)
        .selectAll('line').attr('stroke-opacity', 0.1);

      // Remove domain lines from grid
      g.selectAll('.domain').attr('stroke-opacity', 0.15);

      // Threshold lines
      if (thresholds) {
        for (const th of thresholds) {
          const yPos = yScale(th.value);
          if (!Number.isFinite(yPos)) continue;
          g.append('line')
            .attr('x1', 0).attr('x2', innerWidth)
            .attr('y1', yPos).attr('y2', yPos)
            .attr('stroke', th.color)
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', '6,4')
            .attr('stroke-opacity', 0.7);
          if (th.label) {
            g.append('text')
              .attr('x', innerWidth - 4).attr('y', yPos - 4)
              .attr('text-anchor', 'end')
              .attr('font-size', '10px')
              .attr('fill', th.color)
              .attr('opacity', 0.8)
              .text(th.label);
          }
        }
      }

      // Data lines
      const lineGen = d3.line<TimeSeriesPoint>()
        .x(d => xScale(d.t))
        .y(d => yScale(d.value))
        .defined(d => Number.isFinite(d.t) && Number.isFinite(d.value));

      for (const channel of channels) {
        if (channel.data.length < 2) continue;
        const pathD = lineGen(channel.data);
        if (!pathD) continue;
        const path = g.append('path')
          .attr('d', pathD)
          .attr('fill', 'none')
          .attr('stroke', channel.color)
          .attr('stroke-width', 2);
        if (channel.dashed) {
          path.attr('stroke-dasharray', '5,4');
        }
      }

      // X axis — show relative seconds
      const xAxisTicks = d3.axisBottom(xScale).ticks(6).tickFormat(d => {
        const secAgo = (now - (typeof d === 'number' ? d : Number(d))) / 1000;
        return secAgo <= 0 ? '0s' : `-${secAgo.toFixed(0)}s`;
      });
      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(xAxisTicks)
        .attr('font-size', '10px')
        .attr('color', 'currentColor');

      // Y axis
      const yAxis = d3.axisLeft(yScale).ticks(5).tickFormat(d => formatValue(typeof d === 'number' ? d : Number(d)));
      g.append('g')
        .call(yAxis)
        .attr('font-size', '10px')
        .attr('color', 'currentColor');

      // Y label
      if (yLabel) {
        svg.append('text')
          .attr('transform', `translate(14,${height / 2}) rotate(-90)`)
          .attr('text-anchor', 'middle')
          .attr('font-size', '10px')
          .attr('fill', 'currentColor')
          .attr('opacity', 0.6)
          .text(yLabel);
      }
    } catch (err) {
      console.error('TimeSeriesChart render error:', err);
    }
  }, [channels, height, yLabel, yMin, yMax, minYSpan, thresholds, timeWindow, drawWidth]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || channels.every(c => c.data.length === 0)) return;
    const rect = containerRef.current.getBoundingClientRect();
    const marginLeft = 52;
    const innerWidth = containerRef.current.clientWidth - marginLeft - 14;
    const now = Date.now();
    const tMin = timeWindow ? now - timeWindow * 1000 : Math.min(...channels.flatMap(c => c.data.map(d => d.t)));
    const tMax = timeWindow ? now : Math.max(...channels.flatMap(c => c.data.map(d => d.t)));
    const xScale = d3.scaleLinear().domain([tMin, tMax]).range([0, innerWidth]);
    const x = e.clientX - rect.left - marginLeft;
    const t = xScale.invert(x);
    if (t < tMin || t > tMax) { setTooltip(null); return; }

    const values = channels.map(c => {
      if (c.data.length === 0) return { name: c.name, color: c.color, value: NaN };
      const idx = d3.bisector((d: TimeSeriesPoint) => d.t).left(c.data, t);
      const pt = c.data[Math.min(idx, c.data.length - 1)];
      return { name: c.name, color: c.color, value: pt?.value ?? NaN };
    }).filter(v => Number.isFinite(v.value));

    const secAgo = ((now - t) / 1000).toFixed(1);
    setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, values, time: `-${secAgo}s` });
  }, [channels, timeWindow]);

  const handleMouseLeave = useCallback(() => setTooltip(null), []);
  const hasRealWidth = containerWidth >= CHART_MIN_WIDTH;

  return (
    <div
      ref={containerRef}
      className={cn('w-full min-w-[280px] relative', className)}
      style={{ minHeight: height }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <svg
        ref={svgRef}
        className="overflow-visible block"
        width={hasRealWidth ? containerWidth : drawWidth}
        height={height}
      />
      {showLegend && channels.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs text-muted-foreground">
          {channels.map(c => (
            <span key={c.name} className="inline-flex items-center gap-1.5">
              <span
                className="inline-block w-4 h-0.5"
                style={{
                  backgroundColor: c.color,
                  borderTop: c.dashed ? `2px dashed ${c.color}` : undefined,
                  background: c.dashed ? 'transparent' : c.color,
                }}
              />
              {c.name}
            </span>
          ))}
        </div>
      )}
      {tooltip && tooltip.values.length > 0 && (
        <div
          className="absolute z-10 px-2 py-1.5 rounded bg-popover border border-border text-xs font-mono shadow-md pointer-events-none"
          style={{
            left: Math.min(tooltip.x + 10, (containerWidth || 400) - 200),
            top: Math.max(tooltip.y - 60, 4),
          }}
        >
          <div className="text-muted-foreground mb-0.5">{tooltip.time}</div>
          {tooltip.values.map(v => (
            <div key={v.name} className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: v.color }} />
              <span>{v.name}: {formatValue(v.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
