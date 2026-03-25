/**
 * useWebRTC Hook
 *
 * Custom hook for managing WebRTC connection lifecycle with aiortc-based server
 * Handles peer connection, signaling, auto-reconnect, and stream management
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { SignalingClient } from '@/lib/webrtc/signaling';
import { WEBRTC_CONFIG, PEER_CONNECTION_CONFIG, MAX_RECONNECT_DELAY } from '@/lib/webrtc-config';
import type { WebRTCConnectionState } from '@/types/webrtc';
import { logger } from '@/lib/logger';

const log = logger('useWebRTC');

interface UseWebRTCOptions {
  /**
   * WebRTC signaling server URL (e.g., http://localhost:8081)
   */
  url?: string;

  /**
   * Auto-connect when URL is available
   */
  autoConnect?: boolean;
}

interface UseWebRTCReturn {
  stream: MediaStream | null;
  connectionState: WebRTCConnectionState;
  error: Error | null;
  connect: () => void;
  disconnect: () => void;
}

export function useWebRTC(options: UseWebRTCOptions = {}): UseWebRTCReturn {
  const { url, autoConnect = false } = options;

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [connectionState, setConnectionState] =
    useState<WebRTCConnectionState>('disconnected');
  const [error, setError] = useState<Error | null>(null);

  // Refs for managing connection state and avoiding stale closures
  const signalingRef = useRef<SignalingClient | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const shouldConnectRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const isConnectingRef = useRef(false);
  const isCameraOfflineRef = useRef(false);
  const urlRef = useRef(url);
  
  // Keep urlRef in sync
  useEffect(() => {
    urlRef.current = url;
  }, [url]);

  /**
   * Clear reconnection timeout
   */
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  /**
   * Calculate exponential backoff delay
   */
  const getReconnectDelay = useCallback((): number => {
    // If camera is explicitly offline (503), use a short fixed polling interval
    if (isCameraOfflineRef.current) {
      return 2000; // 2 seconds
    }

    const baseDelay = WEBRTC_CONFIG.reconnectInterval;
    const attempt = reconnectAttemptsRef.current;
    const delay = Math.min(
      baseDelay * Math.pow(2, attempt),
      MAX_RECONNECT_DELAY
    );
    return delay;
  }, []);

  /**
   * Create RTCPeerConnection
   */
  const createPeerConnection = useCallback((): RTCPeerConnection => {
    const pc = new RTCPeerConnection(PEER_CONNECTION_CONFIG);

    // Handle incoming media tracks
    pc.ontrack = (event) => {
      log.info('Received remote track:', {
        kind: event.track.kind,
        trackId: event.track.id,
        trackLabel: event.track.label,
        trackEnabled: event.track.enabled,
        trackMuted: event.track.muted,
        trackReadyState: event.track.readyState,
      });

      // Listen for unmute event (when track starts receiving data)
      event.track.onmute = () => {
        log.warn('Track muted:', event.track.id);
      };

      event.track.onunmute = () => {
        log.info('Track unmuted! Video should now be visible:', event.track.id);
      };

      if (event.streams?.[0]) {
        log.info('Setting remote stream', {
          streamId: event.streams[0].id,
          videoTracks: event.streams[0].getVideoTracks().length,
          audioTracks: event.streams[0].getAudioTracks().length,
        });
        setStream(event.streams[0]);
        setConnectionState('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;
      }
    };

    // Handle ICE candidates (embedded in SDP for aiortc)
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        log.info('ICE candidate:', event.candidate.candidate);
      } else {
        log.info('ICE gathering complete');
      }
    };

    // Handle connection state changes
    pc.onconnectionstatechange = () => {
      log.info('Peer connection state:', pc.connectionState);

      switch (pc.connectionState) {
        case 'connected':
          setConnectionState('connected');
          setError(null);
          reconnectAttemptsRef.current = 0;
          isCameraOfflineRef.current = false;
          isConnectingRef.current = false;
          break;

        case 'disconnected':
          setConnectionState('disconnected');
          setStream(null);
          // Try to reconnect
          if (WEBRTC_CONFIG.autoReconnect && shouldConnectRef.current) {
            // Use a ref to avoid stale closure
            const currentUrl = urlRef.current;
            if (currentUrl) {
              scheduleReconnect();
            }
          }
          break;

        case 'failed':
          setConnectionState('error');
          setError(new Error('Peer connection failed'));
          setStream(null);
          // Try to reconnect
          if (WEBRTC_CONFIG.autoReconnect && shouldConnectRef.current) {
            scheduleReconnect();
          }
          break;

        case 'closed':
          setConnectionState('disconnected');
          setStream(null);
          break;
      }
    };

    // Handle ICE connection state changes
    pc.oniceconnectionstatechange = () => {
      log.info('ICE connection state:', pc.iceConnectionState);
    };

    return pc;
  }, []);

  /**
   * Schedule reconnection with exponential backoff
   */
  const scheduleReconnect = useCallback(() => {
    if (!shouldConnectRef.current) return;

    const maxAttempts = WEBRTC_CONFIG.maxReconnectAttempts;

    // If camera is offline, we want to retry indefinitely without hitting max attempts
    if (isCameraOfflineRef.current) {
      reconnectAttemptsRef.current = 0;
    } else if (maxAttempts > 0 && reconnectAttemptsRef.current >= maxAttempts) {
      log.error('Max reconnection attempts reached');
      setConnectionState('error');
      setError(new Error('Max reconnection attempts reached'));
      return;
    }

    setConnectionState('reconnecting');
    reconnectAttemptsRef.current += 1;

    const delay = getReconnectDelay();
    log.info(
      `Scheduling reconnection in ${delay}ms (attempt ${reconnectAttemptsRef.current})`
    );

    clearReconnectTimeout();
    reconnectTimeoutRef.current = window.setTimeout(() => {
      // Use latest url from ref
      const currentUrl = urlRef.current;
      if (currentUrl && shouldConnectRef.current) {
        performConnect(currentUrl);
      }
    }, delay);
  }, [clearReconnectTimeout, getReconnectDelay]);

  /**
   * Initiate WebRTC connection by sending offer
   */
  const initiateConnection = useCallback(async () => {
    try {
      // Close existing peer connection if present
      if (peerConnectionRef.current) {
        log.info('Closing existing peer connection before reconnecting');
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }

      // Create fresh peer connection
      peerConnectionRef.current = createPeerConnection();
      const pc = peerConnectionRef.current;

      // Add transceiver for receiving video from server
      pc.addTransceiver('video', { direction: 'recvonly' });
      log.info('Added recvonly video transceiver');

      log.info('Creating SDP offer...');

      // Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Wait for ICE gathering to complete (or timeout)
      await new Promise<void>((resolve) => {
        if (pc.iceGatheringState === 'complete') {
          resolve();
        } else {
          const timeout = setTimeout(() => {
            resolve(); // Continue even if not complete
          }, 3000);

          pc.onicegatheringstatechange = () => {
            if (pc.iceGatheringState === 'complete') {
              clearTimeout(timeout);
              resolve();
            }
          };
        }
      });

      log.info('Sending offer to server...');

      // Send offer to server and get answer
      const answer = await signalingRef.current?.sendOffer(
        pc.localDescription!
      );

      if (!answer) {
        throw new Error('No answer received from server');
      }

      // Check if this PC is still the current one
      if (peerConnectionRef.current !== pc) {
        log.info('Peer connection was replaced, ignoring answer');
        isConnectingRef.current = false;
        return;
      }

      // Check if PC was closed during async operation
      if (pc.signalingState === 'closed') {
        log.info('Peer connection was closed, ignoring answer');
        isConnectingRef.current = false;
        return;
      }

      log.info('Setting remote description (answer)...');

      // Set remote description (answer from server)
      await pc.setRemoteDescription(new RTCSessionDescription(answer));

      log.info('WebRTC connection established!');
      isConnectingRef.current = false;
    } catch (err) {
      log.error('Error initiating connection:', err);

      // Check for 503 Service Unavailable (Camera Feed Offline)
      const errorMessage = err instanceof Error ? err.message : String(err);
      const isCameraOffline = errorMessage.includes('503') || errorMessage.includes('Camera feed offline');

      if (isCameraOffline) {
        log.info('Camera feed is offline (503), setting state to disconnected');
        setError(null);
        setConnectionState('disconnected');
        isCameraOfflineRef.current = true;
      } else {
        setError(err as Error);
        setConnectionState('error');
        isCameraOfflineRef.current = false;
      }

      isConnectingRef.current = false;

      // Always try to reconnect (auto-retry logic handles the backoff)
      if (WEBRTC_CONFIG.autoReconnect && shouldConnectRef.current) {
        scheduleReconnect();
      }
    }
  }, [createPeerConnection, scheduleReconnect]);

  /**
   * Internal connect function that performs the actual connection
   */
  const performConnect = useCallback(async (targetUrl: string) => {
    // Don't start a new connection if already connected or connecting
    if (
      isConnectingRef.current ||
      connectionState === 'connected' ||
      connectionState === 'connecting'
    ) {
      log.info('Already connected or connecting, skipping', {
        isConnecting: isConnectingRef.current,
        connectionState,
      });
      return;
    }

    // Set this IMMEDIATELY to block concurrent calls
    isConnectingRef.current = true;
    log.info('Starting connection...');

    try {
      clearReconnectTimeout();
      setConnectionState('connecting');
      setError(null);
      shouldConnectRef.current = true;

      // Create signaling client
      if (!signalingRef.current) {
        signalingRef.current = new SignalingClient(targetUrl);

        // Set up signaling event listeners
        signalingRef.current.on('connected', () => {
          log.info('Signaling connected, initiating WebRTC...');
          void initiateConnection();
        });

        signalingRef.current.on('disconnected', () => {
          log.info('Signaling disconnected');
          if (WEBRTC_CONFIG.autoReconnect && shouldConnectRef.current) {
            scheduleReconnect();
          }
        });

        signalingRef.current.on('error', (err) => {
          log.error('Signaling error:', err);
          setError(err ?? null);
          setConnectionState('error');

          if (WEBRTC_CONFIG.autoReconnect && shouldConnectRef.current) {
            scheduleReconnect();
          }
        });
      }

      // Connect to signaling server
      await signalingRef.current.connect();
    } catch (err) {
      log.error('Failed to connect:', err);
      setError(err as Error);
      setConnectionState('error');
      isConnectingRef.current = false;

      if (WEBRTC_CONFIG.autoReconnect && shouldConnectRef.current) {
        scheduleReconnect();
      }
    }
  }, [connectionState, clearReconnectTimeout, initiateConnection, scheduleReconnect]);

  /**
   * Connect to WebRTC signaling server and establish peer connection
   */
  const connect = useCallback(() => {
    const currentUrl = urlRef.current;
    if (!currentUrl) {
      setError(new Error('WebRTC signaling URL is required'));
      setConnectionState('error');
      return;
    }
    void performConnect(currentUrl);
  }, [performConnect]);

  /**
   * Disconnect from WebRTC
   */
  const disconnect = useCallback(() => {
    log.info('Disconnecting');
    shouldConnectRef.current = false;
    isConnectingRef.current = false;
    clearReconnectTimeout();
    reconnectAttemptsRef.current = 0;

    // Close peer connection
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    setStream(null);
    setConnectionState('disconnected');
    setError(null);
  }, [clearReconnectTimeout]);

  // Auto-connect when URL becomes available
  useEffect(() => {
    if (autoConnect && url && !signalingRef.current) {
      void performConnect(url);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, autoConnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldConnectRef.current = false;
      clearReconnectTimeout();

      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
      }

      if (signalingRef.current) {
        signalingRef.current.disconnect();
      }
    };
  }, [clearReconnectTimeout]);

  return {
    stream,
    connectionState,
    error,
    connect,
    disconnect,
  };
}