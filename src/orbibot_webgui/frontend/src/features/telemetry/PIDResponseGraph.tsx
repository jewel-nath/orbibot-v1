/**
 * PIDResponseGraph - Time vs velocity from /odom while sending /cmd_vel.
 * Vx = forward/back, Vy = strafe, Wz = rotation. Send to command and record; Stop to stop.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { useOdomSampling } from '@/hooks/useOdomSampling';
import { useCmdVel } from '@/hooks/useCmdVel';
import { useRosContext } from '@/contexts/RosContext';
import { Button } from '@/components/ui/button';
import { Play, Square, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const CMD_INTERVAL_MS = 50;   // ~20 Hz
const AUTO_STOP_AFTER_MS = 8000;

const CHART_HEIGHT = 240;
const CHART_MIN_WIDTH = 280;

function LineChart({
  title,
  subtitle,
  unit,
  targetValue,
  samples,
  getValue,
  className,
}: {
  title: string;
  subtitle: string;
  unit: string;
  targetValue: number;
  samples: { t: number; vx: number; vy: number; wz: number }[];
  getValue: (s: { t: number; vx: number; vy: number; wz: number }) => number;
  className?: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setContainerWidth(el.clientWidth);
    });
    ro.observe(el);
    setContainerWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current || containerWidth < CHART_MIN_WIDTH) return;

    const width = containerWidth;
    const height = CHART_HEIGHT;
    const margin = { top: 28, right: 14, bottom: 32, left: 46 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    svg.attr('width', width).attr('height', height);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const maxT = Math.max(1, ...samples.map((s) => s.t), 1);
    const values = samples.map(getValue);
    const allVals = [...values, targetValue].filter((v) => isFinite(v));
    const minV = allVals.length ? Math.min(...allVals) : 0;
    const maxV = allVals.length ? Math.max(...allVals) : 1;
    const padding = (maxV - minV) * 0.1 || 0.1;
    const domainY = [minV - padding, maxV + padding];

    const xScale = d3.scaleLinear().domain([0, maxT]).range([0, innerWidth]);
    const yScale = d3.scaleLinear().domain(domainY).range([innerHeight, 0]);

    // Grid
    g.append('g')
      .attr('class', 'grid')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).ticks(6).tickSize(-innerHeight))
      .selectAll('line')
      .attr('stroke-opacity', 0.12);
    g.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(yScale).ticks(5).tickSize(-innerWidth))
      .selectAll('line')
      .attr('stroke-opacity', 0.12);

    // Target line (horizontal, dashed)
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', yScale(targetValue))
      .attr('y2', yScale(targetValue))
      .attr('stroke', 'hsl(var(--chart-2))')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,4');

    // Actual line (solid)
    if (samples.length >= 2) {
      const line = d3
        .line<{ t: number; v: number }>()
        .x((d) => xScale(d.t))
        .y((d) => yScale(d.v));
      const data = samples.map((s) => ({ t: s.t, v: getValue(s) }));
      g.append('path')
        .attr('d', line(data) ?? '')
        .attr('fill', 'none')
        .attr('stroke', 'hsl(var(--primary))')
        .attr('stroke-width', 2.5);
    }

    // Axes (larger font for clarity)
    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).ticks(6))
      .attr('font-size', '11px')
      .attr('color', 'currentColor');
    g.append('g')
      .call(d3.axisLeft(yScale).ticks(5))
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
  }, [samples, targetValue, getValue, title, subtitle, unit, containerWidth]);

  return (
    <div
      ref={containerRef}
      className={cn('w-full min-w-[260px]', className)}
      style={{ minHeight: CHART_HEIGHT }}
    >
      {containerWidth < CHART_MIN_WIDTH ? (
        <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
          Resizing…
        </div>
      ) : (
        <>
          <svg ref={svgRef} className="overflow-visible" width={containerWidth} height={CHART_HEIGHT} />
          <div className="flex gap-4 mt-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5 border-t-2 border-dashed border-[hsl(var(--chart-2))]" />
              Target
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-4 h-0.5 bg-primary" />
              Actual
            </span>
          </div>
        </>
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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { samples, clearSamples } = useOdomSampling(isRecording);

  const startTest = useCallback(() => {
    if (intervalRef.current || timeoutRef.current) return;
    clearSamples();
    setIsRecording(true);
    setIsSending(true);

    intervalRef.current = setInterval(() => {
      publishVelocity({ vx: targetVx, vy: targetVy, wz: targetWz });
    }, CMD_INTERVAL_MS);

    timeoutRef.current = setTimeout(() => {
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
    };
  }, []);

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
            onClick={clearSamples}
            disabled={isSending || samples.length === 0}
            variant="ghost"
            size="sm"
            className="gap-1.5"
          >
            <Trash2 className="w-4 h-4" />
            Clear
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[280px]">
          <LineChart
            title="Vx"
            subtitle="Forward/back"
            unit="m/s"
            targetValue={targetVx}
            samples={samples}
            getValue={(s) => s.vx}
          />
        </div>
        <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[280px]">
          <LineChart
            title="Vy"
            subtitle="Strafe"
            unit="m/s"
            targetValue={targetVy}
            samples={samples}
            getValue={(s) => s.vy}
          />
        </div>
        <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[280px] md:col-span-2 xl:col-span-1">
          <LineChart
            title="Wz"
            subtitle="Rotate"
            unit="rad/s"
            targetValue={targetWz}
            samples={samples}
            getValue={(s) => s.wz}
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
