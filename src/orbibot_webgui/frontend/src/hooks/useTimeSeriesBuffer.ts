/**
 * useTimeSeriesBuffer - Ring buffer accumulating timestamped values for sparklines.
 *
 * Samples the current value at `sampleInterval` ms and keeps points up to `maxAge` seconds.
 * Uses useRef for the buffer (no re-render on push) and a version counter to trigger
 * re-renders only when new points are added, keeping performance tight.
 */

import { useEffect, useRef, useState } from 'react';

export interface TimeSeriesPoint {
  t: number;    // Unix timestamp in ms
  value: number;
}

interface UseTimeSeriesBufferOptions {
  maxAge?: number;         // seconds of history to keep (default 60)
  sampleInterval?: number; // ms between samples (default 1000)
}

export function useTimeSeriesBuffer(
  currentValue: number | null | undefined,
  options?: UseTimeSeriesBufferOptions
): TimeSeriesPoint[] {
  const { maxAge = 60, sampleInterval = 1000 } = options ?? {};

  const bufferRef = useRef<TimeSeriesPoint[]>([]);
  // Mirror current value into a ref so the interval closure sees updates without
  // needing to be recreated on every value change.
  const valueRef = useRef<number | null | undefined>(currentValue);
  const [, setVersion] = useState(0);

  useEffect(() => {
    valueRef.current = currentValue;
  }, [currentValue]);

  useEffect(() => {
    const id = setInterval(() => {
      const val = valueRef.current;
      if (val == null || !Number.isFinite(val)) return;

      const now = Date.now();
      const cutoff = now - maxAge * 1000;

      // Drop expired points
      const buf = bufferRef.current;
      let start = 0;
      while (start < buf.length && buf[start].t < cutoff) start++;
      if (start > 0) bufferRef.current = buf.slice(start);

      bufferRef.current.push({ t: now, value: val });
      setVersion(v => v + 1);
    }, sampleInterval);

    return () => clearInterval(id);
  }, [maxAge, sampleInterval]);

  return bufferRef.current;
}
