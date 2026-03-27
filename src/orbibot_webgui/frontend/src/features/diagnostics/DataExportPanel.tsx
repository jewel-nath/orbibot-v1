/**
 * DataExportPanel - Record selected ROS topics and export as CSV.
 */

import { useState, useCallback } from 'react';
import { useDataRecorder } from '@/hooks/useDataRecorder';
import { useRosContext } from '@/contexts/RosContext';
import { Button } from '@/components/ui/button';
import { Circle, Square, Download, Trash2 } from 'lucide-react';

const AVAILABLE_TOPICS = [
  { topic: '/odom', messageType: 'nav_msgs/Odometry', label: '/odom' },
  { topic: '/odometry/filtered', messageType: 'nav_msgs/Odometry', label: '/odometry/filtered' },
  { topic: '/imu/data', messageType: 'sensor_msgs/Imu', label: '/imu/data' },
  { topic: '/imu/data_raw', messageType: 'sensor_msgs/Imu', label: '/imu/data_raw' },
  { topic: '/imu/mag', messageType: 'sensor_msgs/MagneticField', label: '/imu/mag' },
  { topic: '/scan', messageType: 'sensor_msgs/LaserScan', label: '/scan' },
  { topic: '/orbibot/encoders', messageType: 'std_msgs/Int32MultiArray', label: '/orbibot/encoders' },
  { topic: '/orbibot/system_status', messageType: 'orbibot_msgs/SystemStatus', label: '/orbibot/system_status' },
  { topic: '/cmd_vel', messageType: 'geometry_msgs/Twist', label: '/cmd_vel' },
  { topic: '/joint_states', messageType: 'sensor_msgs/JointState', label: '/joint_states' },
];

export function DataExportPanel() {
  const { connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';
  const { isRecording, sampleCount, startRecording, stopRecording, exportCSV, clearBuffer } = useDataRecorder();

  const [selected, setSelected] = useState<Set<string>>(
    new Set(['/odom', '/imu/data', '/orbibot/encoders', '/cmd_vel'])
  );

  const toggleTopic = useCallback((topic: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(topic)) next.delete(topic);
      else next.add(topic);
      return next;
    });
  }, []);

  const handleStart = useCallback(() => {
    const topics = AVAILABLE_TOPICS.filter(t => selected.has(t.topic));
    if (topics.length > 0) startRecording(topics);
  }, [selected, startRecording]);

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Select topics to record, then export as CSV for offline analysis.
      </p>

      {/* Topic checkboxes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
        {AVAILABLE_TOPICS.map(t => (
          <label
            key={t.topic}
            className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted/30 cursor-pointer text-xs"
          >
            <input
              type="checkbox"
              checked={selected.has(t.topic)}
              onChange={() => toggleTopic(t.topic)}
              disabled={isRecording}
              className="rounded border-border"
            />
            <span className="font-mono">{t.label}</span>
          </label>
        ))}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        {!isRecording ? (
          <Button
            onClick={handleStart}
            disabled={!isConnected || selected.size === 0}
            size="sm"
            className="gap-1.5"
          >
            <Circle className="w-3.5 h-3.5 fill-red-500 text-red-500" />
            Record
          </Button>
        ) : (
          <Button onClick={stopRecording} variant="destructive" size="sm" className="gap-1.5">
            <Square className="w-3.5 h-3.5" />
            Stop
          </Button>
        )}
        <Button
          onClick={exportCSV}
          disabled={sampleCount === 0}
          variant="outline"
          size="sm"
          className="gap-1.5"
        >
          <Download className="w-3.5 h-3.5" />
          Download CSV
        </Button>
        <Button
          onClick={clearBuffer}
          disabled={sampleCount === 0 || isRecording}
          variant="ghost"
          size="sm"
          className="gap-1.5"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Clear
        </Button>

        {/* Status */}
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          {isRecording && (
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              Recording
            </span>
          )}
          <span className="font-mono">{sampleCount.toLocaleString()} samples</span>
        </div>
      </div>
    </div>
  );
}
