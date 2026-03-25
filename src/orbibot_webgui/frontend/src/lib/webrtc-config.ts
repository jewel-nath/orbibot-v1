/**
 * WebRTC connection configuration.
 */

export const WEBRTC_CONFIG = {
  reconnectInterval: 1000,     // base delay for exponential backoff (ms)
  autoReconnect: true,
  maxReconnectAttempts: 0,     // 0 = unlimited
} as const;

export const PEER_CONNECTION_CONFIG: RTCConfiguration = {
  iceServers: [
    { urls: ['stun:stun.l.google.com:19302'] },
  ],
};

export const MAX_RECONNECT_DELAY = 30000; // 30s cap for exponential backoff
