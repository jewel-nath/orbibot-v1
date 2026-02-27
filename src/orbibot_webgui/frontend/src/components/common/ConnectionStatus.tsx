/**
 * ConnectionStatus - Display ROS connection state with controls
 */

import { useRosContext } from '@/contexts/RosContext';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ConnectionStatus() {
  const { connectionState, error, connect, disconnect, reconnect } = useRosContext();

  const getStatusConfig = () => {
    switch (connectionState) {
      case 'connected':
        return {
          color: 'text-green-500',
          bgColor: 'bg-green-500/10',
          borderColor: 'border-green-500/30',
          icon: <Wifi className="w-4 h-4" />,
          text: 'Connected',
        };
      case 'connecting':
        return {
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-500/10',
          borderColor: 'border-yellow-500/30',
          icon: <Wifi className="w-4 h-4 animate-pulse" />,
          text: 'Connecting...',
        };
      case 'error':
        return {
          color: 'text-red-500',
          bgColor: 'bg-red-500/10',
          borderColor: 'border-red-500/30',
          icon: <WifiOff className="w-4 h-4" />,
          text: 'Connection Error',
        };
      case 'disconnected':
      default:
        return {
          color: 'text-muted-foreground',
          bgColor: 'bg-muted',
          borderColor: 'border-border',
          icon: <WifiOff className="w-4 h-4" />,
          text: 'Disconnected',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="flex items-center gap-2">
      {/* Compact Status Badge */}
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium transition-all duration-200',
          config.bgColor,
          config.borderColor,
          config.color
        )}
        title={error || config.text}
      >
        {config.icon}
        <span className="hidden sm:inline">{config.text}</span>
      </div>

      {/* Control Buttons */}
      <div className="flex items-center gap-1">
        {connectionState === 'connected' ? (
          <button
            onClick={disconnect}
            className="p-2 text-sm bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
            title="Disconnect"
          >
            <WifiOff className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={() => connect()}
            disabled={connectionState === 'connecting'}
            className={cn(
              'p-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
              connectionState === 'connecting' && 'animate-pulse'
            )}
            title="Connect"
          >
            <Wifi className="w-4 h-4" />
          </button>
        )}

        {(connectionState === 'error' || connectionState === 'disconnected') && (
          <button
            onClick={reconnect}
            className="p-2 hover:bg-accent rounded-lg transition-colors border border-border"
            title="Reconnect"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}