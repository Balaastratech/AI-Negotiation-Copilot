/**
 * AudioWorkletManager
 * Manages capture and playback AudioWorklets for Gemini Live API.
 * Replaces MediaStreamManager's audio functions entirely.
 * 
 * IMPORTANT: Call cleanup() on component unmount or session end.
 */
export class AudioWorkletManager {
  private captureContext: AudioContext | null = null;
  private playbackContext: AudioContext | null = null;
  private captureWorkletNode: AudioWorkletNode | null = null;
  private playbackWorkletNode: AudioWorkletNode | null = null;
  private micStream: MediaStream | null = null;
  private onAudioChunk: ((buffer: ArrayBuffer) => void) | null = null;

  /**
   * Start microphone capture.
   * Returns a stream of Int16 PCM ArrayBuffers at 16kHz.
   * Each chunk is ~4096 samples (~256ms of audio).
   */
  async startCapture(onChunk: (buffer: ArrayBuffer) => void): Promise<void> {
    this.onAudioChunk = onChunk;

    // AudioContext at 16kHz forces browser to downsample from 44.1/48kHz
    this.captureContext = new AudioContext({ sampleRate: 16000 });

    await this.captureContext.audioWorklet.addModule('/worklets/pcm-processor.js');

    this.micStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      video: false,
    });

    const source = this.captureContext.createMediaStreamSource(this.micStream);
    this.captureWorkletNode = new AudioWorkletNode(
      this.captureContext,
      'pcm-capture-processor'
    );

    this.captureWorkletNode.port.onmessage = (event: MessageEvent) => {
      if (this.onAudioChunk) {
        this.onAudioChunk(event.data as ArrayBuffer);
      }
    };

    source.connect(this.captureWorkletNode);
    this.captureWorkletNode.connect(this.captureContext.destination);
  }

  /**
   * Initialize audio playback for Gemini responses.
   * Call this before the session starts, not after first audio arrives.
   */
  async initPlayback(): Promise<void> {
    // Playback context at 24kHz to match Gemini output
    this.playbackContext = new AudioContext({ sampleRate: 24000 });
    await this.playbackContext.audioWorklet.addModule('/worklets/pcm-playback-processor.js');

    this.playbackWorkletNode = new AudioWorkletNode(
      this.playbackContext,
      'pcm-playback-processor'
    );

    this.playbackWorkletNode.connect(this.playbackContext.destination);
  }

  /**
   * Feed a PCM chunk received from Gemini into the playback worklet.
   * chunk: ArrayBuffer of Int16 PCM at 24kHz
   */
  playChunk(chunk: ArrayBuffer): void {
    if (!this.playbackWorkletNode) return;
    // Transfer ownership of buffer to worklet thread (zero-copy)
    this.playbackWorkletNode.port.postMessage(chunk, [chunk]);
  }

  /**
   * Stop mic capture without stopping playback.
   */
  stopCapture(): void {
    this.micStream?.getTracks().forEach(t => t.stop());
    this.captureWorkletNode?.disconnect();
    this.captureContext?.close();
    this.micStream = null;
    this.captureWorkletNode = null;
    this.captureContext = null;
  }

  /**
   * Full cleanup — call on session end or component unmount.
   */
  cleanup(): void {
    this.stopCapture();
    this.playbackWorkletNode?.disconnect();
    this.playbackContext?.close();
    this.playbackWorkletNode = null;
    this.playbackContext = null;
    this.onAudioChunk = null;
  }

  get isCapturing(): boolean {
    return this.captureContext !== null && this.captureContext.state === 'running';
  }
}
