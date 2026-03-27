/**
 * ConnectionHealthPanel - Monitor message rates and staleness for key ROS topics.
 */

import { useEffect, useRef, useState } from 'react';
import ROSLIB from 'roslib';
import { useRosContext } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';

interface TopicConfig {
  topic: string;
  messageType: string;
  expectedHz: number;
}

const MONITORED_TOPICS: TopicConfig[] = [
  { topic: '/odom', messageType: 'nav_msgs/Odometry', expectedHz: 20 },
  { topic: '/odometry/filtered', messageType: 'nav_msgs/Odometry', expectedHz: 20 },
  { topic: '/imu/data', messageType: 'sensor_msgs/Imu', expectedHz: 50 },
  { topic: '/scan', messageType: 'sensor_msgs/LaserScan', expectedHz: 10 },
  { topic: '/orbibot/encoders', messageType: 'std_msgs/Int32MultiArray', expectedHz: 5 },
  { topic: '/orbibot/system_status', messageType: 'orbibot_msgs/SystemStatus', expectedHz: 10 },
  { topic: '/orbibot/safety_status', messageType: 'orbibot_msgs/SafetyStatus', expectedHz: 10 },
  { topic: '/joint_states', messageType: 'sensor_msgs/JointState', expectedHz: 50 },
];

interface TopicStat {
  topic: string;
  expectedHz: number;
  actualHz: number;
  lastReceived: number; // timestamp
  messageCount: number;
}

export function ConnectionHealthPanel() {
  const { ros, connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';

  const statsRef = useRef<Map<string, { timestamps: number[]; lastReceived: number; count: number }>>(new Map());
  const [stats, setStats] = useState<TopicStat[]>([]);

  useEffect(() => {
    if (!ros || !isConnected) {
      statsRef.current.clear();
      setStats([]);
      return;
    }

    const topics: ROSLIB.Topic[] = [];

    for (const config of MONITORED_TOPICS) {
      const entry = { timestamps: [] as number[], lastReceived: 0, count: 0 };
      statsRef.current.set(config.topic, entry);

      const topic = new ROSLIB.Topic({
        ros,
        name: config.topic,
        messageType: config.messageType,
        throttle_rate: 0,
      });

      topic.subscribe(() => {
        const now = Date.now();
        entry.lastReceived = now;
        entry.count++;
        entry.timestamps.push(now);
        // Keep last 100 timestamps
        if (entry.timestamps.length > 100) {
          entry.timestamps = entry.timestamps.slice(-100);
        }
      });

      topics.push(topic);
    }

    // Update display stats every second
    const interval = setInterval(() => {
      const now = Date.now();
      const result: TopicStat[] = MONITORED_TOPICS.map(config => {
        const entry = statsRef.current.get(config.topic);
        if (!entry || entry.timestamps.length < 2) {
          return {
            topic: config.topic,
            expectedHz: config.expectedHz,
            actualHz: 0,
            lastReceived: entry?.lastReceived ?? 0,
            messageCount: entry?.count ?? 0,
          };
        }
        // Compute Hz from recent timestamps
        const recent = entry.timestamps.filter(t => t > now - 5000);
        const hz = recent.length >= 2
          ? (recent.length - 1) / ((recent[recent.length - 1] - recent[0]) / 1000)
          : 0;
        return {
          topic: config.topic,
          expectedHz: config.expectedHz,
          actualHz: hz,
          lastReceived: entry.lastReceived,
          messageCount: entry.count,
        };
      });
      setStats(result);
    }, 1000);

    return () => {
      clearInterval(interval);
      for (const topic of topics) topic.unsubscribe();
      statsRef.current.clear();
    };
  }, [ros, isConnected]);

  if (!isConnected) {
    return <p className="text-sm text-muted-foreground">Connect to ROS to monitor topic health.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-muted-foreground">
            <th className="text-left py-2 pr-4 font-medium">Topic</th>
            <th className="text-right py-2 px-2 font-medium">Expected</th>
            <th className="text-right py-2 px-2 font-medium">Actual</th>
            <th className="text-right py-2 px-2 font-medium">Last Received</th>
            <th className="text-center py-2 pl-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {stats.map(s => {
            const now = Date.now();
            const secAgo = s.lastReceived > 0 ? (now - s.lastReceived) / 1000 : Infinity;
            const ratio = s.expectedHz > 0 ? s.actualHz / s.expectedHz : 0;
            const isStale = secAgo > 3;
            const isLow = ratio < 0.5 && !isStale;
            const isOk = ratio >= 0.5 && !isStale;

            return (
              <tr key={s.topic} className="border-b border-border/40">
                <td className="py-1.5 pr-4 font-mono text-xs">{s.topic}</td>
                <td className="py-1.5 px-2 text-right font-mono text-xs">{s.expectedHz} Hz</td>
                <td className="py-1.5 px-2 text-right font-mono text-xs">
                  {s.actualHz > 0 ? s.actualHz.toFixed(1) : '—'} Hz
                </td>
                <td className="py-1.5 px-2 text-right text-xs text-muted-foreground">
                  {s.lastReceived > 0 ? (secAgo < 1 ? '<1s ago' : `${secAgo.toFixed(0)}s ago`) : 'Never'}
                </td>
                <td className="py-1.5 pl-2 text-center">
                  <span className={cn(
                    'inline-block w-2.5 h-2.5 rounded-full',
                    isOk && 'bg-green-500',
                    isLow && 'bg-yellow-500',
                    isStale && 'bg-red-500',
                    !s.lastReceived && 'bg-muted-foreground/30',
                  )} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
