/**
 * WebRTC type definitions
 */

export type WebRTCConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

export interface WebRTCConfig {
  /**
   * WebRTC server URL (e.g., http://localhost:8080)
   */
  serverUrl: string;

  /**
   * Auto-reconnect on connection loss
   */
  autoReconnect: boolean;

  /**
   * Initial reconnection interval (will use exponential backoff)
   */
  reconnectInterval: number;

  /**
   * Maximum reconnection attempts (0 = infinite)
   */
  maxReconnectAttempts: number;

  /**
   * ICE servers configuration
   */
  iceServers: RTCIceServer[];
}

export interface SignalingEvents {
  connected: () => void;
  disconnected: () => void;
  error: (error: Error) => void;
}

export interface OfferResponse {
  sdp: string;
  type: RTCSdpType;
}
