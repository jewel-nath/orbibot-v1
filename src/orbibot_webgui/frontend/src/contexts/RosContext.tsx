/**
 * RosContext - Simplified single-robot ROS connection
 *
 * Unlike the reference dashboard which manages multiple robots,
 * this context maintains a single connection to ws://localhost:9090
 */

import { createContext, useContext, useEffect, useState, useRef } from 'react';
import type { ReactNode } from 'react';
import ROSLIB from 'roslib';
import type { ConnectionState } from '@/types/ros';
import { WS_CONFIG } from '@/lib/constants';
import { toast } from 'sonner';

interface RosContextValue {
  ros: ROSLIB.Ros | null;
  connectionState: ConnectionState;
  error: string | null;
  connect: (url?: string) => void;
  disconnect: () => void;
  reconnect: () => void;
}

const RosContext = createContext<RosContextValue | undefined>(undefined);

interface RosProviderProps {
  children: ReactNode;
  autoConnect?: boolean;
  url?: string;
}

import { useSettings } from './SettingsContext';

export function RosProvider({ children, autoConnect = true, url = WS_CONFIG.defaultUrl }: RosProviderProps) {
  const { settings } = useSettings();
  const [ros, setRos] = useState<ROSLIB.Ros | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  // Use settings.websocketUrl if available, otherwise fall back to prop/default
  const [wsUrl, setWsUrl] = useState<string>(settings.websocketUrl || url);

  // Update wsUrl when settings change
  useEffect(() => {
    if (settings.websocketUrl && settings.websocketUrl !== wsUrl) {
      setWsUrl(settings.websocketUrl);
    }
  }, [settings.websocketUrl]);


  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  // Ref tracks the current ROS instance so cleanup doesn't close a stale reference
  const rosRef = useRef<ROSLIB.Ros | null>(null);

  const clearReconnectTimeout = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  };

  const connect = (newUrl?: string) => {
    const targetUrl = newUrl || wsUrl;

    // Clean up existing connection
    if (ros) {
      ros.close();
    }

    clearReconnectTimeout();
    setConnectionState('connecting');
    setError(null);
    setWsUrl(targetUrl);

    console.log(`[RosContext] Connecting to ${targetUrl}...`);

    const newRos = new ROSLIB.Ros({
      url: targetUrl,
    });

    newRos.on('connection', () => {
      console.log('[RosContext] Connected to ROS bridge');
      setConnectionState('connected');
      setError(null);
      reconnectAttemptsRef.current = 0;

      toast.success('Connected to OrbiBot', {
        description: targetUrl,
        duration: 3000,
      });
    });

    newRos.on('error', (err) => {
      console.error('[RosContext] Connection error:', err);
      setConnectionState('error');
      setError(err.message || 'Connection error');

      // Attempt reconnection if under max attempts
      if (reconnectAttemptsRef.current < WS_CONFIG.maxReconnectAttempts) {
        reconnectAttemptsRef.current += 1;
        console.log(`[RosContext] Reconnecting in ${WS_CONFIG.reconnectDelay}ms (attempt ${reconnectAttemptsRef.current}/${WS_CONFIG.maxReconnectAttempts})`);

        toast.warning(`Connection lost. Retrying...`, {
          description: `Attempt ${reconnectAttemptsRef.current}/${WS_CONFIG.maxReconnectAttempts}`,
          duration: 2000,
        });

        reconnectTimeoutRef.current = setTimeout(() => {
          connect(targetUrl);
        }, WS_CONFIG.reconnectDelay);
      } else {
        console.error('[RosContext] Max reconnection attempts reached');

        toast.error('Failed to connect to OrbiBot', {
          description: err.message || 'Max reconnection attempts reached',
          duration: 5000,
        });
      }
    });

    newRos.on('close', () => {
      console.log('[RosContext] Connection closed');
      setConnectionState('disconnected');

      toast.info('Disconnected from OrbiBot', {
        duration: 2000,
      });
    });

    rosRef.current = newRos;
    setRos(newRos);
  };

  const disconnect = () => {
    console.log('[RosContext] Disconnecting...');
    clearReconnectTimeout();
    reconnectAttemptsRef.current = 0;

    if (ros) {
      ros.close();
      setRos(null);
      rosRef.current = null;
    }

    setConnectionState('disconnected');
    setError(null);
  };

  const reconnect = () => {
    console.log('[RosContext] Manual reconnect triggered');
    reconnectAttemptsRef.current = 0;
    connect(wsUrl);
  };

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount — use ref to avoid closing a stale ROS instance
    return () => {
      clearReconnectTimeout();
      if (rosRef.current) {
        rosRef.current.close();
        rosRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value: RosContextValue = {
    ros,
    connectionState,
    error,
    connect,
    disconnect,
    reconnect,
  };

  return <RosContext.Provider value={value}>{children}</RosContext.Provider>;
}

/**
 * Hook to access ROS connection
 * Throws error if used outside RosProvider
 */
export function useRosContext() {
  const context = useContext(RosContext);
  if (context === undefined) {
    throw new Error('useRosContext must be used within a RosProvider');
  }
  return context;
}

/**
 * Compatibility hook for new components
 */
export function useRos() {
  const context = useRosContext();
  return {
    ...context,
    isConnected: context.connectionState === 'connected',
  };
}
