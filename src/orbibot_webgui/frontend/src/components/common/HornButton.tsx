/**
 * HornButton - Publishes a 200ms beep to /orbibot/beep (std_msgs/UInt16)
 *
 * Buzzer protocol: data=0 off, data=1 continuous, data≥10 on for N ms then auto-off
 */

import { useState, useCallback } from 'react';
import { Volume2 } from 'lucide-react';
import { usePublisher } from '@/hooks/usePublisher';
import { useRosContext } from '@/contexts/RosContext';
import { ROS_TOPICS, ROS_MESSAGE_TYPES } from '@/lib/constants';
import { cn } from '@/lib/utils';

const BEEP_DURATION_MS = 200;

export function HornButton() {
  const { connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';
  const [active, setActive] = useState(false);

  const publish = usePublisher<{ data: number }>({
    topic: ROS_TOPICS.beep,
    messageType: ROS_MESSAGE_TYPES.uint16,
  });

  const handleBeep = useCallback(() => {
    if (!isConnected || active) return;
    publish({ data: BEEP_DURATION_MS });
    setActive(true);
    setTimeout(() => setActive(false), BEEP_DURATION_MS);
  }, [isConnected, active, publish]);

  return (
    <button
      onClick={handleBeep}
      disabled={!isConnected}
      title="Beep horn (200ms)"
      className={cn(
        'flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-150',
        'border border-border/50',
        isConnected
          ? active
            ? 'bg-yellow-500 text-black border-yellow-400 scale-95'
            : 'bg-card hover:bg-muted text-muted-foreground hover:text-foreground'
          : 'opacity-40 cursor-not-allowed bg-card text-muted-foreground'
      )}
    >
      <Volume2 className={cn('w-4 h-4', active && 'animate-pulse')} />
    </button>
  );
}
