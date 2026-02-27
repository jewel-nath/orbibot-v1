/**
 * WebRTCContext - Global context provider for WebRTC connection management
 *
 * Manages a single WebRTC connection shared across all video components
 * Uses REST-based signaling compatible with aiortc backend
 */

import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { useWebRTC } from '@/hooks/useWebRTC';
import type { WebRTCConnectionState } from '@/types/webrtc';

interface WebRTCContextValue {
  stream: MediaStream | null;
  connectionState: WebRTCConnectionState;
  error: Error | null;
  connect: () => void;
  disconnect: () => void;
}

interface WebRTCProviderProps {
  children: ReactNode;
  webrtcUrl?: string;
  autoConnect?: boolean;
}

const WebRTCContext = createContext<WebRTCContextValue | undefined>(undefined);

import { useSettings } from './SettingsContext';

// ...

export function WebRTCProvider({ children, webrtcUrl, autoConnect = false }: WebRTCProviderProps) {
  const { settings } = useSettings();
  // Single WebRTC connection for the entire app
  const { stream, connectionState, error, connect, disconnect } = useWebRTC({
    url: settings.webrtcUrl || webrtcUrl,
    autoConnect,
  });

  const value: WebRTCContextValue = {
    stream,
    connectionState,
    error,
    connect,
    disconnect,
  };

  return (
    <WebRTCContext.Provider value={value}>{children}</WebRTCContext.Provider>
  );
}

/**
 * Hook to access WebRTC connection
 * Throws error if used outside WebRTCProvider
 */
export function useWebRTCContext() {
  const context = useContext(WebRTCContext);

  if (context === undefined) {
    throw new Error('useWebRTCContext must be used within a WebRTCProvider');
  }

  return context;
}
