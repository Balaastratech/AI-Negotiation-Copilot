import { AudioWorkletManager } from './audio-worklet-manager';

/**
 * NegotiationWebSocket
 * Bridges the AudioWorkletManager streams with the backend WebSocket.
 * 
 * Handles bidirectional separation of text (JSON control signals)
 * and binary (raw PCM audio) frames.
 */
export class NegotiationWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private audioManager: AudioWorkletManager;
  private messageListeners: Set<(message: any) => void> = new Set();
  private closeListeners: Set<() => void> = new Set();
  private errorListeners: Set<(error: any) => void> = new Set();
  private pendingConnection: { resolve: () => void, reject: (reason?: any) => void } | null = null;

  constructor(url: string, audioManager: AudioWorkletManager) {
    this.url = url;
    this.audioManager = audioManager;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.pendingConnection = { resolve, reject };
      this.ws = new WebSocket(this.url);
      
      // We expect binary data for audio
      this.ws.binaryType = 'arraybuffer';

      this.ws.onopen = () => {
        if (this.pendingConnection) {
          this.pendingConnection.resolve();
          this.pendingConnection = null;
        }
      };

      this.ws.onerror = (error) => {
        if (this.pendingConnection) {
          this.pendingConnection.reject(error);
          this.pendingConnection = null;
        } else {
          // Propagate errors occurring after initial connection
          this.errorListeners.forEach(listener => listener(error));
        }
      };

      this.ws.onclose = () => {
        if (this.pendingConnection) {
          this.pendingConnection.reject(new Error('WebSocket closed before connection established'));
          this.pendingConnection = null;
        }
        this.closeListeners.forEach(listener => listener());
      };

      this.ws.onmessage = (event: MessageEvent) => {
        if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
          // BINARY frame = PCM audio from Gemini (24kHz Int16)
          if (event.data instanceof Blob) {
            event.data.arrayBuffer().then(buf => this.audioManager.playChunk(buf));
          } else {
            this.audioManager.playChunk(event.data as ArrayBuffer);
          }
        } else {
          // TEXT frame = JSON control message
          try {
            const message = JSON.parse(event.data as string);
            this.messageListeners.forEach(listener => listener(message));
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        }
      };
    });
  }

  disconnect(): void {
    if (this.pendingConnection) {
      this.pendingConnection.reject(new Error('WebSocket disconnected before connection established'));
      this.pendingConnection = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Send a raw 16kHz Int16 PCM ArrayBuffer directly as a binary frame
   */
  sendAudioChunk(buffer: ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(buffer);
    }
  }

  /**
   * Send a standard JSON control message (e.g. strategy choices, start commands)
   */
  sendControl(type: string, payload: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    }
  }

  onMessage(listener: (message: any) => void): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  onClose(listener: () => void): () => void {
    this.closeListeners.add(listener);
    return () => this.closeListeners.delete(listener);
  }

  onError(listener: (error: any) => void): () => void {
    this.errorListeners.add(listener);
    return () => this.errorListeners.delete(listener);
  }
}
