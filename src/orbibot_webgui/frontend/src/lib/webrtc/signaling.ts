/**
 * WebRTC signaling client for OrbiBot camera streaming.
 *
 * Connects to the WebRTC server (default port 8081) and handles
 * SDP offer/answer exchange via HTTP POST.
 */

type EventType = 'connected' | 'disconnected' | 'error';
type EventCallback = (err?: Error) => void;

export class SignalingClient {
  private _url: string;
  public connected = false;
  private _listeners: Map<EventType, EventCallback[]> = new Map();

  constructor(url: string) {
    this._url = url;
  }

  on(event: EventType, callback: EventCallback): void {
    const existing = this._listeners.get(event) || [];
    existing.push(callback);
    this._listeners.set(event, existing);
  }

  private _emit(event: EventType, err?: Error): void {
    const callbacks = this._listeners.get(event) || [];
    for (const cb of callbacks) {
      try {
        cb(err);
      } catch (e) {
        console.error(`[SignalingClient] Event handler error for '${event}':`, e);
      }
    }
  }

  async connect(): Promise<void> {
    try {
      // Health check to confirm the server is reachable
      const resp = await fetch(this._url, {
        signal: AbortSignal.timeout(5000),
      });
      if (!resp.ok) {
        throw new Error(`Server responded with ${resp.status}`);
      }
      this.connected = true;
      this._emit('connected');
    } catch (err) {
      this.connected = false;
      const error = err instanceof Error ? err : new Error(String(err));
      this._emit('error', error);
      throw error;
    }
  }

  async sendOffer(offer: RTCSessionDescriptionInit): Promise<RTCSessionDescriptionInit> {
    const resp = await fetch(`${this._url}/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sdp: offer.sdp,
        type: offer.type,
      }),
    });

    if (!resp.ok) {
      throw new Error(`Offer failed: HTTP ${resp.status}`);
    }

    const answer = await resp.json() as { sdp: string; type: RTCSdpType };
    return {
      sdp: answer.sdp,
      type: answer.type,
    };
  }

  disconnect(): void {
    this.connected = false;
    this._listeners.clear();
    this._emit('disconnected');
  }
}
