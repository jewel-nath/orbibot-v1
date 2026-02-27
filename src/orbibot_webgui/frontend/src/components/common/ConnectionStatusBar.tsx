/**
 * ConnectionStatusBar - Shows connection status warnings
 *
 * Features:
 * - Shows warning when ROS is disconnected
 * - Shows warning when offline
 * - Auto-dismisses when reconnected
 * - Compact design that doesn't obstruct UI
 */

import { useState, useEffect } from 'react';
import { Wifi, WifiOff, Server, X } from 'lucide-react';
import { useRosContext } from '@/contexts/RosContext';
import { useNetworkStatus } from '@/hooks/useNetworkStatus';
import { cn } from '@/lib/utils';

interface ConnectionStatusBarProps {
  className?: string;
}

export function ConnectionStatusBar({ className }: ConnectionStatusBarProps) {
  const { connectionState, error: rosError } = useRosContext();
  const { isOnline, wasOffline } = useNetworkStatus();
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [showReconnected, setShowReconnected] = useState(false);

  const isRosConnected = connectionState === 'connected';
  const isRosConnecting = connectionState === 'connecting';

  // Show "reconnected" message briefly when coming back online
  useEffect(() => {
    if (isOnline && wasOffline) {
      setShowReconnected(true);
      setDismissed(null);
      const timer = setTimeout(() => setShowReconnected(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [isOnline, wasOffline]);

  // Reset dismissed state when connection changes
  useEffect(() => {
    if (isRosConnected && isOnline) {
      setDismissed(null);
    }
  }, [isRosConnected, isOnline]);

  // Determine what to show
  const getStatus = () => {
    if (!isOnline) {
      return {
        type: 'offline' as const,
        icon: <WifiOff className="w-4 h-4" />,
        message: 'No internet connection',
        variant: 'error' as const,
      };
    }

    if (showReconnected) {
      return {
        type: 'reconnected' as const,
        icon: <Wifi className="w-4 h-4" />,
        message: 'Back online',
        variant: 'success' as const,
      };
    }

    if (!isRosConnected && !isRosConnecting) {
      return {
        type: 'ros_disconnected' as const,
        icon: <Server className="w-4 h-4" />,
        message: rosError || 'ROS bridge disconnected',
        variant: 'warning' as const,
      };
    }

    if (isRosConnecting) {
      return {
        type: 'ros_connecting' as const,
        icon: <Server className="w-4 h-4 animate-pulse" />,
        message: 'Connecting to ROS...',
        variant: 'info' as const,
      };
    }

    return null;
  };

  const status = getStatus();

  // Don't show if no status or if dismissed
  if (!status || dismissed === status.type) {
    return null;
  }

  const variantStyles = {
    error: 'bg-red-500 text-white',
    warning: 'bg-yellow-500 text-black',
    success: 'bg-green-500 text-white',
    info: 'bg-blue-500 text-white',
  };

  return (
    <div
      className={cn(
        'fixed top-0 left-0 right-0 z-50',
        'flex items-center justify-center gap-2 px-4 py-2',
        'text-sm font-medium',
        variantStyles[status.variant],
        className
      )}
      role="alert"
    >
      {status.icon}
      <span>{status.message}</span>

      {status.variant !== 'success' && (
        <button
          onClick={() => setDismissed(status.type)}
          className="ml-2 p-1 hover:bg-black/10 rounded transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

/**
 * Inline connection indicator for use in headers/toolbars
 */
interface ConnectionIndicatorProps {
  className?: string;
  showText?: boolean;
}

export function ConnectionIndicator({
  className,
  showText = true,
}: ConnectionIndicatorProps) {
  const { connectionState } = useRosContext();
  const { isOnline } = useNetworkStatus();

  const isConnected = connectionState === 'connected' && isOnline;
  const isConnecting = connectionState === 'connecting';

  return (
    <div
      className={cn(
        'flex items-center gap-2 text-sm',
        isConnected && 'text-green-500',
        isConnecting && 'text-yellow-500',
        !isConnected && !isConnecting && 'text-red-500',
        className
      )}
    >
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          isConnected && 'bg-green-500',
          isConnecting && 'bg-yellow-500 animate-pulse',
          !isConnected && !isConnecting && 'bg-red-500'
        )}
      />
      {showText && (
        <span className="text-xs font-medium">
          {!isOnline
            ? 'Offline'
            : isConnected
              ? 'Connected'
              : isConnecting
                ? 'Connecting...'
                : 'Disconnected'}
        </span>
      )}
    </div>
  );
}
