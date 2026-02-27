/**
 * ExplorationPanel - Control panel for autonomous frontier exploration
 *
 * Features:
 * - Start/Pause/Resume/Stop exploration controls
 * - Status display from orbibot_exploration node
 * - Frontier count visualization
 * - Map save functionality
 * - Integration with orbibot_exploration ROS 2 package
 *
 * Topics:
 * - /orbibot/exploration/command (String) - send: start, stop, pause, resume
 * - /orbibot/exploration/status (String) - receive: idle, exploring, navigating, etc.
 * - /orbibot/exploration/frontiers (MarkerArray) - frontier visualization
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Compass,
  Play,
  Pause,
  Square,
  Save,
  Map,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Navigation,
  Home,
  RotateCcw,
} from 'lucide-react';
import { useRosContext } from '@/contexts/RosContext';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { ROS_TOPICS } from '@/lib/constants';
import ROSLIB from 'roslib';

// Match the states from orbibot_exploration/frontier_explorer.py
type ExplorationStatus =
  | 'idle'
  | 'exploring'
  | 'navigating'
  | 'returning'
  | 'complete'
  | 'stopped'
  | 'error';

interface ExplorationPanelProps {
  className?: string;
}

export function ExplorationPanel({ className }: ExplorationPanelProps) {
  const { ros, connectionState } = useRosContext();
  const isConnected = connectionState === 'connected';

  const [status, setStatus] = useState<ExplorationStatus>('idle');
  const [frontierCount, setFrontierCount] = useState(0);
  const [isSavingMap, setIsSavingMap] = useState(false);
  const [explorationAvailable, setExplorationAvailable] = useState(false);

  // Refs for publisher/subscribers
  const commandPublisherRef = useRef<ROSLIB.Topic | null>(null);

  // Setup command publisher
  useEffect(() => {
    if (!ros || !isConnected) {
      commandPublisherRef.current = null;
      return;
    }

    commandPublisherRef.current = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.explorationCommand,
      messageType: 'std_msgs/String',
    });

    return () => {
      commandPublisherRef.current = null;
    };
  }, [ros, isConnected]);

  // Subscribe to exploration status
  useEffect(() => {
    if (!ros || !isConnected) {
      setExplorationAvailable(false);
      return;
    }

    let messageReceived = false;

    const statusTopic = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.explorationStatus,
      messageType: 'std_msgs/String',
    });

    const handleStatus = (msg: ROSLIB.Message) => {
      // Mark exploration as available when we receive first message
      if (!messageReceived) {
        messageReceived = true;
        setExplorationAvailable(true);
      }

      const { data } = msg as unknown as { data: string };
      // Map the status string to our type
      const validStatuses: ExplorationStatus[] = [
        'idle',
        'exploring',
        'navigating',
        'returning',
        'complete',
        'stopped',
      ];
      if (validStatuses.includes(data as ExplorationStatus)) {
        setStatus(data as ExplorationStatus);
      }
    };

    // Set a timeout to check if we receive any message
    const availabilityTimeout = setTimeout(() => {
      if (!messageReceived) {
        setExplorationAvailable(false);
      }
    }, 3000); // Wait 3 seconds for first message

    statusTopic.subscribe(handleStatus);

    return () => {
      statusTopic.unsubscribe();
      clearTimeout(availabilityTimeout);
    };
  }, [ros, isConnected]);

  // Subscribe to frontier markers for count
  useEffect(() => {
    if (!ros || !isConnected) return;

    const frontierTopic = new ROSLIB.Topic({
      ros,
      name: ROS_TOPICS.explorationFrontiers,
      messageType: 'visualization_msgs/MarkerArray',
    });

    const handleFrontiers = (msg: ROSLIB.Message) => {
      const { markers } = msg as unknown as { markers: Array<{ action?: number; ns?: string }> };
      // Count frontier markers (namespace 'frontiers', action != DELETE)
      const activeFrontiers = markers.filter(
        (m) => m.action !== 2 && m.ns === 'frontiers'
      ).length;
      setFrontierCount(activeFrontiers);
    };

    frontierTopic.subscribe(handleFrontiers);

    return () => {
      frontierTopic.unsubscribe();
    };
  }, [ros, isConnected]);

  // Send command to exploration node
  const sendCommand = useCallback(
    (command: 'start' | 'stop' | 'pause' | 'resume') => {
      if (!commandPublisherRef.current) {
        toast.error('Not connected to ROS');
        return;
      }

      const message = new ROSLIB.Message({ data: command });
      commandPublisherRef.current.publish(message);

      // Show toast based on command
      switch (command) {
        case 'start':
          toast.success('Exploration started', {
            description: 'Robot is exploring unknown areas',
          });
          break;
        case 'pause':
          toast.info('Exploration paused');
          break;
        case 'resume':
          toast.success('Exploration resumed');
          break;
        case 'stop':
          toast.info('Exploration stopped');
          break;
      }
    },
    []
  );

  // Control functions
  const startExploration = useCallback(() => sendCommand('start'), [sendCommand]);
  const pauseExploration = useCallback(() => sendCommand('pause'), [sendCommand]);
  const resumeExploration = useCallback(() => sendCommand('resume'), [sendCommand]);
  const stopExploration = useCallback(() => sendCommand('stop'), [sendCommand]);

  // Save current map
  const saveMap = useCallback(() => {
    if (!ros) return;

    setIsSavingMap(true);

    // Call map_saver service (from nav2_map_server)
    const saveService = new ROSLIB.Service({
      ros,
      name: '/map_saver/save_map',
      serviceType: 'nav2_msgs/SaveMap',
    });

    const request = new ROSLIB.ServiceRequest({
      map_topic: '/map',
      map_url: 'orbibot_map',
      image_format: 'pgm',
      map_mode: 'trinary',
      free_thresh: 0.25,
      occupied_thresh: 0.65,
    });

    saveService.callService(
      request,
      (response: { result: boolean }) => {
        setIsSavingMap(false);
        if (response.result) {
          toast.success('Map saved successfully', {
            description: 'Map saved as orbibot_map.pgm',
          });
        } else {
          toast.error('Failed to save map');
        }
      },
      (error: string) => {
        setIsSavingMap(false);
        console.error('Failed to save map:', error);
        toast.error('Failed to save map', {
          description: 'Make sure map_saver is running',
        });
      }
    );
  }, [ros]);

  // Keyboard shortcuts for exploration
  useKeyboardShortcuts(
    [
      {
        key: 'x',
        description: 'Start/Resume exploration',
        category: 'exploration',
        action: () => {
          if (isConnected) {
            if (status === 'idle' || status === 'stopped' || status === 'complete') {
              startExploration();
            } else if (status === 'exploring' || status === 'navigating') {
              pauseExploration();
            } else {
              resumeExploration();
            }
          }
        },
        enabled: isConnected,
      },
      {
        key: 'Escape',
        description: 'Stop exploration',
        category: 'exploration',
        action: () => {
          if (isConnected && status !== 'idle' && status !== 'stopped') {
            stopExploration();
          }
        },
        enabled: isConnected && status !== 'idle' && status !== 'stopped',
      },
      {
        key: 's',
        modifiers: { ctrl: true },
        description: 'Save map',
        category: 'exploration',
        action: () => {
          if (isConnected && !isSavingMap) {
            saveMap();
          }
        },
        enabled: isConnected,
      },
    ],
    { enabled: isConnected }
  );

  // Status indicator color and icon
  const getStatusDisplay = () => {
    switch (status) {
      case 'exploring':
        return {
          color: 'text-green-500',
          bgColor: 'bg-green-500/10',
          icon: <Compass className="w-4 h-4 animate-spin" />,
          text: 'Finding Frontiers',
        };
      case 'navigating':
        return {
          color: 'text-blue-500',
          bgColor: 'bg-blue-500/10',
          icon: <Navigation className="w-4 h-4" />,
          text: 'Navigating',
        };
      case 'returning':
        return {
          color: 'text-orange-500',
          bgColor: 'bg-orange-500/10',
          icon: <Home className="w-4 h-4" />,
          text: 'Returning Home',
        };
      case 'complete':
        return {
          color: 'text-green-500',
          bgColor: 'bg-green-500/10',
          icon: <CheckCircle2 className="w-4 h-4" />,
          text: 'Complete',
        };
      case 'stopped':
        return {
          color: 'text-muted-foreground',
          bgColor: 'bg-muted',
          icon: <Square className="w-4 h-4" />,
          text: 'Stopped',
        };
      case 'error':
        return {
          color: 'text-red-500',
          bgColor: 'bg-red-500/10',
          icon: <AlertCircle className="w-4 h-4" />,
          text: 'Error',
        };
      default: // idle
        return {
          color: 'text-muted-foreground',
          bgColor: 'bg-muted',
          icon: <CheckCircle2 className="w-4 h-4" />,
          text: 'Ready',
        };
    }
  };

  const statusDisplay = getStatusDisplay();

  // Determine which buttons to show
  const isActive = ['exploring', 'navigating', 'returning'].includes(status);
  const canStart = ['idle', 'stopped', 'complete'].includes(status);

  return (
    <div className={cn('p-4 bg-card rounded-lg border', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Compass className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Frontier Exploration</h3>
        </div>
        <div
          className={cn(
            'flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium',
            statusDisplay.bgColor,
            statusDisplay.color
          )}
        >
          {statusDisplay.icon}
          <span>{statusDisplay.text}</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="p-3 bg-muted/50 rounded-lg">
          <div className="text-xs text-muted-foreground mb-1">Frontiers Found</div>
          <div className="text-2xl font-bold text-primary">{frontierCount}</div>
        </div>
        <div className="p-3 bg-muted/50 rounded-lg">
          <div className="text-xs text-muted-foreground mb-1">Status</div>
          <div className="text-sm font-medium capitalize">{status}</div>
        </div>
      </div>

      {/* Progress indicator for active states */}
      {isActive && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>
              {status === 'navigating'
                ? 'Moving to frontier...'
                : status === 'returning'
                  ? 'Returning to start...'
                  : 'Searching for frontiers...'}
            </span>
            <Loader2 className="w-3 h-3 animate-spin" />
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full transition-all duration-500 animate-pulse',
                status === 'navigating' ? 'bg-blue-500' :
                status === 'returning' ? 'bg-orange-500' : 'bg-purple-500'
              )}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          {canStart ? (
            <button
              onClick={startExploration}
              disabled={!isConnected || !explorationAvailable}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg',
                'bg-primary text-primary-foreground font-medium',
                'hover:bg-primary/90 transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              title={!explorationAvailable ? 'Exploration node not running' : ''}
            >
              <Play className="w-4 h-4" />
              {status === 'complete' ? 'Explore Again' : 'Start Exploration'}
            </button>
          ) : (
            <button
              onClick={pauseExploration}
              disabled={!isConnected || !explorationAvailable}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-yellow-600 text-white font-medium hover:bg-yellow-700 transition-colors disabled:opacity-50"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          )}

          {isActive && (
            <button
              onClick={stopExploration}
              disabled={!isConnected || !explorationAvailable}
              className="px-4 py-2 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
              title="Stop exploration"
            >
              <Square className="w-4 h-4" />
            </button>
          )}

          {status === 'stopped' && (
            <button
              onClick={resumeExploration}
              disabled={!isConnected || !explorationAvailable}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
              title="Resume exploration"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Save Map Button */}
        <button
          onClick={saveMap}
          disabled={!isConnected || isSavingMap}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg',
            'border hover:bg-muted/50 transition-colors',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {isSavingMap ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          <span>{isSavingMap ? 'Saving...' : 'Save Map'}</span>
        </button>
      </div>

      {/* Connection warning */}
      {!isConnected && (
        <div className="mt-3 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-xs text-yellow-500 text-center">
            Connect to ROS to enable exploration controls
          </p>
        </div>
      )}

      {/* Info */}
      <div className="mt-3 pt-3 border-t">
        <p className="text-xs text-muted-foreground text-center">
          <Map className="w-3 h-3 inline mr-1" />
          orbibot_exploration - Frontier-based autonomous exploration
        </p>
      </div>
    </div>
  );
}
