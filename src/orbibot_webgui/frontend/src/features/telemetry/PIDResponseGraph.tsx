/**
 * PIDResponseGraph - Time vs velocity from /odom while sending /cmd_vel.
 * Vx = forward/back, Vy = strafe, Wz = rotation. Send to command and record; Stop to stop.
 * Improvements: readable Y-axis for small values, per-chart metrics, hover tooltip.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { useOdomSampling } from '@/hooks/useOdomSampling';
import { useCmdVel } from '@/hooks/useCmdVel';
import { useRosContext } from '@/contexts/RosContext';
import { Button } from '@/components/ui/button';
import { Play, Square, Trash2, Timer } from 'lucide-react';
import { cn } from '@/lib/utils';

const CMD_INTERVAL_MS = 50;   // ~20 Hz
const AUTO_STOP_AFTER_MS = 8000;

const CHART_HEIGHT = 260;
const CHART_MIN_WIDTH = 280;
/** Fallback width when container width not yet available (e.g. initial layout) */
const CHART_FALLBACK_WIDTH = 400;

/** Minimum Y-axis span so small values (e.g. Vy, Wz near 0) stay readable */
const MIN_Y_SPAN_LINEAR = 0.008;  // m/s
const MIN_Y_SPAN_ANGULAR = 0.008; // rad/s

type Sample = { t: number; vx: number; vy: number; wz: number };

function computeMetrics(
  samples: Sample[],
  targetValue: number,
  getValue: (s: Sample) => number
): { mae: number; maxError: number; overshootPct: number } {
  if (samples.length === 0) return { mae: 0, maxError: 0, overshootPct: 0 };
  const target = Number.isFinite(targetValue) ? targetValue : 0;
  const values: number[] = samples.map((s) => getValue(s)).filter((v): v is number => Number.isFinite(v));
  if (values.length === 0) return { mae: 0, maxError: 0, overshootPct: 0 };
  const errors = values.map((v) => Math.abs(v - target));
  const mae = errors.reduce((a, b) => a + b, 0) / errors.length;
  const maxError = Math.max(...errors);
  let overshootPct = 0;
  if (target !== 0 && Math.abs(target) > 1e-9) {
    const maxVal = Math.max(...values);
    const minVal = Math.min(...values);
    if (target > 0 && maxVal > target) overshootPct = ((maxVal - target) / target) * 100;
    else if (target < 0 && minVal < target) overshootPct = ((minVal - target) / target) * 100;
  }
  return {
    mae: Number.isFinite(mae) ? mae : 0,
    maxError: Number.isFinite(maxError) ? maxError : 0,
    overshootPct: Number.isFinite(overshootPct) ? overshootPct : 0,
  };
}

function domainWithMinSpan(minV: number, maxV: number, minSpan: number): [number, number] {
  const lo = Number.isFinite(minV) ? minV : 0;
  const hi = Number.isFinite(maxV) ? maxV : 1;
  const span = hi - lo;
  if (!Number.isFinite(span) || span < minSpan) {
    const half = minSpan / 2;
    const mid = (lo + hi) / 2;
    return [mid - half, mid + half];
  }
  const padding = span * 0.1 || 0.1;
  return [lo - padding, hi + padding];
}

function formatAxisValue(_unit: string, v: number): string {
  const x = Number.isFinite(v) ? v : 0;
  const abs = Math.abs(x);
  if (abs >= 1) return x.toFixed(2);
  if (abs >= 0.01) return x.toFixed(3);
  if (abs >= 0.001) return x.toFixed(4);
  return x.toExponential(1);
}

function LineChart({
  title,
  subtitle,
  unit,
  targetValue,
  samples,
  getValue,
  minYSpan,
  className,
}: {
  title: string;
  subtitle: string;
  unit: string;
  targetValue: number;
  samples: Sample[];
  getValue: (s: Sample) => number;
  minYSpan: number;
  className?: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [tooltip, setTooltip] = useState<{ t: number; actual: number; target: number; x: number; y: number } | null>(null);

  const metrics = computeMetrics(samples, targetValue, getValue);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateWidth = () => setContainerWidth(el.clientWidth);
    const ro = new ResizeObserver(updateWidth);
    ro.observe(el);
    updateWidth();
    // Re-read after layout in case initial read was 0
    const t = setTimeout(updateWidth, 50);
    return () => {
      clearTimeout(t);
      ro.disconnect();
    };
  }, []);

  const drawWidth = containerWidth >= CHART_MIN_WIDTH ? containerWidth : CHART_FALLBACK_WIDTH;

  useEffect(() => {
    if (!svgRef.current) return;

    try {
      const width = drawWidth;
      const height = CHART_HEIGHT;
      const margin = { top: 28, right: 14, bottom: 32, left: 52 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('width', width).attr('height', height);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const maxT = Math.max(1, ...samples.map((s) => s.t), 1);
    const values = samples.map((s) => getValue(s));
    const allVals = [...values, targetValue].filter((v) => Number.isFinite(v));
    const minV = allVals.length ? Math.min(...allVals) : 0;
    const maxV = allVals.length ? Math.max(...allVals) : 1;
    const domainY = domainWithMinSpan(minV, maxV, minYSpan);
    let yMin = Math.min(domainY[0], domainY[1]);
    let yMax = Math.max(domainY[0], domainY[1]);
    if (!Number.isFinite(yMin)) yMin = -minYSpan / 2;
    if (!Number.isFinite(yMax)) yMax = minYSpan / 2;
    if (yMax <= yMin) {
      const mid = (yMin + yMax) / 2;
      yMin = mid - minYSpan / 2;
      yMax = mid + minYSpan / 2;
    }
    const safeDomainY: [number, number] = [yMin, yMax];

    const xScale = d3.scaleLinear().domain([0, maxT]).range([0, innerWidth]);
    const yScale = d3.scaleLinear().domain(safeDomainY).range([innerHeight, 0]);

    const yAxis = d3
      .axisLeft(yScale)
      .ticks(5)
      .tickFormat((d) => formatAxisValue(unit, typeof d === 'number' ? d : Number(d)));
    const yAxisGrid = d3.axisLeft(yScale).ticks(5).tickSize(-innerWidth).tickFormat(() => '');
    const xAxisGrid = d3.axisBottom(xScale).ticks(6).tickSize(-innerHeight).tickFormat(() => '');

    // Grid only (no labels — labels drawn once in Axes below to avoid duplicate/blurred text)
    g.append('g')
      .attr('class', 'grid')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(xAxisGrid)
      .selectAll('line')
      .attr('stroke-opacity', 0.12);
    g.append('g')
      .attr('class', 'grid')
      .call(yAxisGrid)
      .selectAll('line')
      .attr('stroke-opacity', 0.12);

    // Target line (horizontal, dashed)
    const targetNum = Number.isFinite(targetValue) ? targetValue : 0;
    const yTarget = yScale(targetNum);
    if (Number.isFinite(yTarget)) {
      g.append('line')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', yTarget)
        .attr('y2', yTarget)
        .attr('stroke', 'hsl(var(--chart-2))')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '5,4');
    }

    // Actual line (solid) — only use finite points so path doesn't get NaN
    if (samples.length >= 2) {
      const line = d3
        .line<{ t: number; v: number }>()
        .x((d) => xScale(d.t))
        .y((d) => yScale(d.v))
        .defined((d) => Number.isFinite(d.t) && Number.isFinite(d.v));
      const data = samples.map((s) => ({ t: s.t, v: getValue(s) }));
      const pathD = line(data);
      if (pathD) {
        g.append('path')
          .attr('d', pathD)
          .attr('fill', 'none')
          .attr('stroke', 'hsl(var(--primary))')
          .attr('stroke-width', 2.5);
      }
    }

    // Axes (larger font for clarity)
    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).ticks(6))
      .attr('font-size', '11px')
      .attr('color', 'currentColor');
    g.append('g')
      .call(yAxis)
      .attr('font-size', '11px')
      .attr('color', 'currentColor');

    // Title: variable name + description
    svg
      .append('text')
      .attr('x', margin.left)
      .attr('y', 14)
      .attr('font-size', '13px')
      .attr('font-weight', '700')
      .attr('fill', 'currentColor')
      .text(title);
    svg
      .append('text')
      .attr('x', margin.left)
      .attr('y', 26)
      .attr('font-size', '11px')
      .attr('fill', 'currentColor')
      .attr('opacity', 0.85)
      .text(`${subtitle} (${unit})`);
    } catch (err) {
      console.error('PIDResponseGraph LineChart render error:', err);
    }
  }, [samples, targetValue, getValue, title, subtitle, unit, drawWidth, minYSpan]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!containerRef.current || samples.length === 0) return;
      const rect = containerRef.current.getBoundingClientRect();
      const marginLeft = 52;
      const innerWidth = containerRef.current.clientWidth - marginLeft - 14;
      const maxT = Math.max(1, ...samples.map((s) => s.t), 1);
      const xScale = d3.scaleLinear().domain([0, maxT]).range([0, innerWidth]);
      const x = e.clientX - rect.left - marginLeft;
      const t = xScale.invert(x);
      if (t < 0 || t > maxT) {
        setTooltip(null);
        return;
      }
      const idx = d3.bisector((s: Sample) => s.t).left(samples, t);
      const s = samples[Math.min(idx, samples.length - 1)];
      setTooltip({
        t: s.t,
        actual: getValue(s),
        target: targetValue,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    },
    [samples, targetValue, getValue]
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  const hasRealWidth = containerWidth >= CHART_MIN_WIDTH;

  return (
    <div
      ref={containerRef}
      className={cn('w-full min-w-[280px] relative', className)}
      style={{ minHeight: CHART_HEIGHT }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <svg
        ref={svgRef}
        className="overflow-visible block"
        width={hasRealWidth ? containerWidth : drawWidth}
        height={CHART_HEIGHT}
      />
      {!hasRealWidth && containerWidth > 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground pointer-events-none">
          Resizing…
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 border-t-2 border-dashed border-[hsl(var(--chart-2))]" />
          Target
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5 bg-primary" />
          Actual
        </span>
        {samples.length > 0 && (
          <span className="ml-auto font-mono text-[10px] opacity-90">
            MAE: {formatAxisValue(unit, metrics.mae)} · Max err: {formatAxisValue(unit, metrics.maxError)}
            {metrics.overshootPct > 0 && ` · Overshoot: ${metrics.overshootPct.toFixed(1)}%`}
          </span>
        )}
      </div>
      {tooltip && (
        <div
          className="absolute z-10 px-2 py-1 rounded bg-popover border border-border text-xs font-mono shadow-md pointer-events-none"
          style={{
            left: Math.min(tooltip.x + 10, containerWidth - 180),
            top: Math.min(tooltip.y + 8, CHART_HEIGHT - 56),
          }}
        >
          t = {tooltip.t.toFixed(2)} s · actual = {formatAxisValue(unit, tooltip.actual)} · target = {formatAxisValue(unit, tooltip.target)}
        </div>
      )}
    </div>
  );
}

export function PIDResponseGraph() {
  const { connectionState } = useRosContext();
  const { publishVelocity, stop } = useCmdVel();
  const [targetVx, setTargetVx] = useState(0.2);
  const [targetVy, setTargetVy] = useState(0);
  const [targetWz, setTargetWz] = useState(0);
  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSec, setElapsedSec] = useState<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timerIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const t0Ref = useRef<number>(0);

  const { samples, clearSamples } = useOdomSampling(isRecording);

  const startTest = useCallback(() => {
    if (intervalRef.current || timeoutRef.current) return;
    clearSamples();
    setIsRecording(true);
    setIsSending(true);
    t0Ref.current = Date.now();
    setElapsedSec(0);

    timerIntervalRef.current = setInterval(() => {
      setElapsedSec((Date.now() - t0Ref.current) / 1000);
    }, 100);

    intervalRef.current = setInterval(() => {
      publishVelocity({ vx: targetVx, vy: targetVy, wz: targetWz });
    }, CMD_INTERVAL_MS);

    timeoutRef.current = setTimeout(() => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
      setElapsedSec((Date.now() - t0Ref.current) / 1000);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      stop();
      setIsSending(false);
      setIsRecording(false);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    }, AUTO_STOP_AFTER_MS);
  }, [targetVx, targetVy, targetWz, publishVelocity, stop, clearSamples]);

  const stopTest = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setElapsedSec((Date.now() - t0Ref.current) / 1000);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    stop();
    setIsSending(false);
    setIsRecording(false);
  }, [stop]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}:${sec.toFixed(1)}` : `${sec.toFixed(1)} s`;
  };

  const isConnected = connectionState === 'connected';

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        <strong>Vx</strong> = forward/back, <strong>Vy</strong> = strafe left/right, <strong>Wz</strong> = rotate.
        Set targets, then Send to command the robot and record from /odom. Stop ends early. Auto-stops after 8 s.
      </p>

      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground font-medium">Vx (m/s) — forward/back</span>
          <input
            type="number"
            step={0.05}
            min={-1}
            max={1}
            value={targetVx}
            onChange={(e) => setTargetVx(parseFloat(e.target.value) || 0)}
            disabled={isSending}
            className="w-24 px-2 py-1.5 rounded border border-border bg-background text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground font-medium">Vy (m/s) — strafe</span>
          <input
            type="number"
            step={0.05}
            min={-1}
            max={1}
            value={targetVy}
            onChange={(e) => setTargetVy(parseFloat(e.target.value) || 0)}
            disabled={isSending}
            className="w-24 px-2 py-1.5 rounded border border-border bg-background text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground font-medium">Wz (rad/s) — rotate</span>
          <input
            type="number"
            step={0.1}
            min={-2}
            max={2}
            value={targetWz}
            onChange={(e) => setTargetWz(parseFloat(e.target.value) || 0)}
            disabled={isSending}
            className="w-24 px-2 py-1.5 rounded border border-border bg-background text-sm"
          />
        </label>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex gap-2">
            <Button
              onClick={startTest}
              disabled={!isConnected || isSending}
              size="sm"
              className="gap-1.5"
            >
              <Play className="w-4 h-4" />
              Send
            </Button>
            <Button
              onClick={stopTest}
              disabled={!isSending}
              variant="outline"
              size="sm"
              className="gap-1.5"
            >
              <Square className="w-4 h-4" />
              Stop
            </Button>
            <Button
              onClick={() => {
                clearSamples();
                if (!isSending) setElapsedSec(0);
              }}
              disabled={isSending || samples.length === 0}
              variant="ghost"
              size="sm"
              className="gap-1.5"
            >
              <Trash2 className="w-4 h-4" />
              Clear
            </Button>
          </div>
          <div
            className={cn(
              'flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-mono tabular-nums',
              isSending
                ? 'border-primary/50 bg-primary/10 text-primary'
                : 'border-border bg-muted/30 text-muted-foreground'
            )}
          >
            <Timer className="h-4 w-4 shrink-0" />
            <span>{formatElapsed(elapsedSec)}</span>
            {isSending && <span className="text-xs font-normal text-muted-foreground">(running)</span>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[300px]">
          <LineChart
            title="Vx"
            subtitle="Forward/back"
            unit="m/s"
            targetValue={targetVx}
            samples={samples}
            getValue={(s) => s.vx}
            minYSpan={MIN_Y_SPAN_LINEAR}
          />
        </div>
        <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[300px]">
          <LineChart
            title="Vy"
            subtitle="Strafe"
            unit="m/s"
            targetValue={targetVy}
            samples={samples}
            getValue={(s) => s.vy}
            minYSpan={MIN_Y_SPAN_LINEAR}
          />
        </div>
        <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[300px] md:col-span-2 xl:col-span-1">
          <LineChart
            title="Wz"
            subtitle="Rotate"
            unit="rad/s"
            targetValue={targetWz}
            samples={samples}
            getValue={(s) => s.wz}
            minYSpan={MIN_Y_SPAN_ANGULAR}
          />
        </div>
      </div>

      {!isConnected && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Connect to ROS and run the robot stack to see response data.
        </p>
      )}
    </div>
  );
}
