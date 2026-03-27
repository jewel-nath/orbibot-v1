/**
 * useMultiChannelTimeSeries - N-channel ring buffer for time-series charts.
 *
 * Samples all channels simultaneously at `sampleInterval` ms and keeps
 * points up to `maxAge` seconds. Ref-based buffers with version counter
 * for efficient re-rendering.
 */

import { useEffect, useRef, useState } from 'react';
import { type TimeSeriesPoint } from './useTimeSeriesBuffer';

export interface MultiChannelData {
  [channelName: string]: TimeSeriesPoint[];
}

interface UseMultiChannelTimeSeriesOptions {
  maxAge?: number;         // seconds of history (default 60)
  sampleInterval?: number; // ms between samples (default 200)
}

export function useMultiChannelTimeSeries(
  currentValues: Record<string, number | null | undefined>,
  options?: UseMultiChannelTimeSeriesOptions
): MultiChannelData {
  const { maxAge = 60, sampleInterval = 200 } = options ?? {};

  const buffersRef = useRef<Record<string, TimeSeriesPoint[]>>({});
  const valuesRef = useRef(currentValues);
  const [, setVersion] = useState(0);

  useEffect(() => {
    valuesRef.current = currentValues;
  }, [currentValues]);

  useEffect(() => {
    const id = setInterval(() => {
      const now = Date.now();
      const cutoff = now - maxAge * 1000;
      const vals = valuesRef.current;
      let changed = false;

      for (const key of Object.keys(vals)) {
        const v = vals[key];
        if (v == null || !Number.isFinite(v)) continue;

        if (!buffersRef.current[key]) {
          buffersRef.current[key] = [];
        }

        const buf = buffersRef.current[key];

        // Drop expired points
        let start = 0;
        while (start < buf.length && buf[start].t < cutoff) start++;
        if (start > 0) buffersRef.current[key] = buf.slice(start);

        buffersRef.current[key].push({ t: now, value: v });
        changed = true;
      }

      if (changed) setVersion(v => v + 1);
    }, sampleInterval);

    return () => clearInterval(id);
  }, [maxAge, sampleInterval]);

  return buffersRef.current;
}
