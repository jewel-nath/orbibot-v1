/**
 * useDataRecorder - Record ROS topic messages to memory for CSV export.
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';

export interface RecordedRow {
  timestamp: number;
  topic: string;
  [key: string]: unknown;
}

interface TopicConfig {
  topic: string;
  messageType: string;
}

interface DataRecorderState {
  isRecording: boolean;
  sampleCount: number;
  startRecording: (topics: TopicConfig[]) => void;
  stopRecording: () => void;
  exportCSV: () => void;
  clearBuffer: () => void;
}

const MAX_SAMPLES = 10000;

function flattenMessage(msg: Record<string, unknown>, prefix = ''): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(msg)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value != null && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(result, flattenMessage(value as Record<string, unknown>, fullKey));
    } else if (Array.isArray(value)) {
      result[fullKey] = value.join(';');
    } else {
      result[fullKey] = String(value ?? '');
    }
  }
  return result;
}

export function useDataRecorder(): DataRecorderState {
  const { ros, connectionState } = useRosContext();
  const [isRecording, setIsRecording] = useState(false);
  const [sampleCount, setSampleCount] = useState(0);
  const bufferRef = useRef<RecordedRow[]>([]);
  const subsRef = useRef<ROSLIB.Topic[]>([]);

  const stopRecording = useCallback(() => {
    for (const topic of subsRef.current) {
      topic.unsubscribe();
    }
    subsRef.current = [];
    setIsRecording(false);
  }, []);

  const startRecording = useCallback((topics: TopicConfig[]) => {
    if (!ros || connectionState !== 'connected') return;

    // Clear previous
    stopRecording();
    bufferRef.current = [];
    setSampleCount(0);
    setIsRecording(true);

    for (const config of topics) {
      const topic = new ROSLIB.Topic({
        ros,
        name: config.topic,
        messageType: config.messageType,
      });

      topic.subscribe((msg) => {
        if (bufferRef.current.length >= MAX_SAMPLES) return;
        const flat = flattenMessage(msg as Record<string, unknown>);
        bufferRef.current.push({
          timestamp: Date.now(),
          topic: config.topic,
          ...flat,
        });
        setSampleCount(bufferRef.current.length);
      });

      subsRef.current.push(topic);
    }
  }, [ros, connectionState, stopRecording]);

  const exportCSV = useCallback(() => {
    if (bufferRef.current.length === 0) return;

    // Collect all unique column names
    const columns = new Set<string>();
    for (const row of bufferRef.current) {
      for (const key of Object.keys(row)) columns.add(key);
    }
    const cols = Array.from(columns);

    const header = cols.join(',');
    const rows = bufferRef.current.map(row =>
      cols.map(c => {
        const val = row[c];
        const str = String(val ?? '');
        return str.includes(',') ? `"${str}"` : str;
      }).join(',')
    );

    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `orbibot_recording_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const clearBuffer = useCallback(() => {
    bufferRef.current = [];
    setSampleCount(0);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      for (const topic of subsRef.current) topic.unsubscribe();
      subsRef.current = [];
    };
  }, []);

  return { isRecording, sampleCount, startRecording, stopRecording, exportCSV, clearBuffer };
}
