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
  private onSilenceDetected: (() => void) | null = null;
  private onSpeechDetected: (() => void) | null = null;
  private silenceTimer: NodeJS.Timeout | null = null;
  private isSpeaking: boolean = false;
  private readonly SILENCE_THRESHOLD_MS = 500; // 500ms - much more aggressive

  /**
   * Start microphone capture.
   * Returns a stream of Int16 PCM ArrayBuffers at 16kHz.
   * Each chunk is ~4096 samples (~256ms of audio).
   */
  async startCapture(
    onChunk: (buffer: ArrayBuffer) => void,
    onSilence?: () => void,
    onSpeech?: () => void
  ): Promise<void> {
    this.onAudioChunk = onChunk;
    this.onSilenceDetected = onSilence || null;
    this.onSpeechDetected = onSpeech || null;

    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) throw new Error("AudioContext not supported in this browser.");

    // AudioContext at 16kHz forces browser to downsample from 44.1/48kHz
    this.captureContext = new AudioContextClass({ sampleRate: 16000 });

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
        
        // Detect speech activity based on audio data
        const audioData = new Int16Array(event.data as ArrayBuffer);
        const hasAudio = this.detectAudio(audioData);
        
        if (hasAudio) {
          // User is speaking
          if (!this.isSpeaking) {
            this.isSpeaking = true;
            if (this.onSpeechDetected) {
              this.onSpeechDetected();
            }
          }
          // Reset silence timer
          if (this.silenceTimer) {
            clearTimeout(this.silenceTimer);
          }
          // Start new silence timer
          this.silenceTimer = setTimeout(() => {
            this.isSpeaking = false;
            if (this.onSilenceDetected) {
              this.onSilenceDetected();
            }
          }, this.SILENCE_THRESHOLD_MS);
        }
      }
    };

    source.connect(this.captureWorkletNode);
    this.captureWorkletNode.connect(this.captureContext.destination);
  }

  /**
   * Simple audio detection based on RMS energy
   */
  private detectAudio(samples: Int16Array): boolean {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    const rms = Math.sqrt(sum / samples.length);
    // Threshold for speech detection (adjust if needed)
    return rms > 500;
  }

  /**
   * Initialize audio playback for Gemini responses.
   * Call this before the session starts, not after first audio arrives.
   */
  async initPlayback(): Promise<void> {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) throw new Error("AudioContext not supported in this browser.");

    // Playback context at 24kHz to match Gemini output
    this.playbackContext = new AudioContextClass({ sampleRate: 24000 });

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
    if (!this.playbackWorkletNode) {
      console.error('[AudioManager] playChunk called but playback not initialized!');
      return;
    }
    if (!this.playbackContext) {
      console.error('[AudioManager] playChunk called but playback context not initialized!');
      return;
    }
    // Transfer ownership of buffer to worklet thread (zero-copy)
    this.playbackWorkletNode.port.postMessage(chunk, [chunk]);
  }

  /**
   * Stop mic capture without stopping playback.
   */
  stopCapture(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    this.isSpeaking = false;
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
