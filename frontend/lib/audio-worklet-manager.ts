// ─── Types ────────────────────────────────────────────────────────────────────

export type Speaker = 'USER' | 'COUNTERPARTY';

export type CaptureState = 'idle' | 'starting' | 'capturing' | 'stopping' | 'error';
export type PlaybackState = 'idle' | 'initializing' | 'ready' | 'error';

export interface AudioManagerConfig {
  /** RMS threshold for speech detection. Default: 500 */
  silenceThreshold?: number;
  /** Milliseconds of silence before firing onSilence. Default: 500 */
  silenceDebounceMs?: number;
  /** Sample rate for capture. Default: 16000 */
  captureSampleRate?: number;
  /** Sample rate for playback (Gemini output). Default: 24000 */
  playbackSampleRate?: number;
}

export interface CaptureCallbacks {
  onChunk: (buffer: ArrayBuffer) => void;
  onSilence?: () => void;
  onSpeech?: () => void;
  onStateChange?: (state: CaptureState) => void;
  onError?: (error: AudioManagerError) => void;
}

// ─── Errors ───────────────────────────────────────────────────────────────────

export class AudioManagerError extends Error {
  constructor(
    message: string,
    public readonly code: AudioErrorCode,
    public readonly cause?: unknown
  ) {
    super(message);
    this.name = 'AudioManagerError';
  }
}

export enum AudioErrorCode {
  CONTEXT_CREATION_FAILED = 'CONTEXT_CREATION_FAILED',
  WORKLET_LOAD_FAILED = 'WORKLET_LOAD_FAILED',
  MIC_ACCESS_DENIED = 'MIC_ACCESS_DENIED',
  CAPTURE_NOT_STARTED = 'CAPTURE_NOT_STARTED',
  PLAYBACK_NOT_INITIALIZED = 'PLAYBACK_NOT_INITIALIZED',
  INVALID_STATE = 'INVALID_STATE',
  CONTEXT_SUSPENDED = 'CONTEXT_SUSPENDED',
}

// ─── AudioWorkletManager ──────────────────────────────────────────────────────

/**
 * AudioWorkletManager
 *
 * Manages microphone capture and audio playback for the Gemini Live API.
 * - Capture outputs Int16 PCM @ 16kHz (raw ArrayBuffers, no base64).
 * - Playback expects Int16 PCM @ 24kHz ArrayBuffers from Gemini.
 *
 * Lifecycle:
 *   1. new AudioWorkletManager(config?)
 *   2. await startCapture(cbs)    — starts mic
 *   3. await initPlayback()       — prepares playback pipeline
 *   4. playChunk(buffer)          — feed Gemini audio
 *   5. stopCapture()              — mic off, playback stays alive
 *   6. cleanup()                  — full teardown
 */
export class AudioWorkletManager {
  // ── Config ──────────────────────────────────────────────────────────────────

  private readonly cfg: Required<AudioManagerConfig> = {
    silenceThreshold: 50,
    silenceDebounceMs: 1500,  // keep speaking window open longer
    captureSampleRate: 16000,
    playbackSampleRate: 24000,
  };

  // ── State ───────────────────────────────────────────────────────────────────

  private captureState: CaptureState = 'idle';
  private playbackState: PlaybackState = 'idle';
  private _bypassVAD = false; // when true, send all audio regardless of silence

  // ── Capture resources ───────────────────────────────────────────────────────

  private captureCtx: AudioContext | null = null;
  private captureNode: AudioWorkletNode | null = null;
  private micStream: MediaStream | null = null;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;
  private isSpeaking = false;

  // ── Playback resources ──────────────────────────────────────────────────────

  private playbackCtx: AudioContext | null = null;
  private playbackNode: AudioWorkletNode | null = null;

  // ── Callbacks ───────────────────────────────────────────────────────────────

  private callbacks: CaptureCallbacks | null = null;

  // ────────────────────────────────────────────────────────────────────────────

  constructor(config: AudioManagerConfig = {}) {
    Object.assign(this.cfg, config);
  }

  // ── Public: capture ─────────────────────────────────────────────────────────

  /**
   * Start microphone capture. Resolves when the pipeline is live.
   * Emits raw Int16 PCM ArrayBuffers at 16kHz via `callbacks.onChunk`.
   */
  async startCapture(callbacks: CaptureCallbacks): Promise<void> {
    if (this.captureState !== 'idle' && this.captureState !== 'error') {
      throw new AudioManagerError(
        `Cannot start capture in state "${this.captureState}"`,
        AudioErrorCode.INVALID_STATE
      );
    }

    this.callbacks = callbacks;
    this.setCaptureState('starting');

    try {
      this.captureCtx = await this.createAudioContext(this.cfg.captureSampleRate);
      await this.loadWorklet(this.captureCtx, '/worklets/pcm-processor.js');

      this.micStream = await this.requestMicrophone();
      const source = this.captureCtx.createMediaStreamSource(this.micStream);
      this.captureNode = new AudioWorkletNode(this.captureCtx, 'pcm-capture-processor');
      this.captureNode.port.onmessage = this.handleCaptureMessage;

      source.connect(this.captureNode);
      // Connect to destination so the AudioContext scheduler stays alive
      this.captureNode.connect(this.captureCtx.destination);

      this.setCaptureState('capturing');
    } catch (err) {
      this.setCaptureState('error');
      const wrapped = this.wrapError(err);
      this.callbacks?.onError?.(wrapped);
      await this.teardownCapture();
      throw wrapped;
    }
  }

  /**
   * Stop microphone capture. Playback is unaffected.
   * Safe to call from any capture state.
   */
  stopCapture(): void {
    if (this.captureState === 'idle') return;
    this.setCaptureState('stopping');
    this.teardownCapture();
    this.setCaptureState('idle');
  }

  /**
   * Records audio for a specific duration and returns the combined chunk.
   * This is a self-contained, one-shot recording method.
   */
  async startRecording(durationMs: number): Promise<ArrayBuffer | null> {
    if (this.captureState !== 'idle') {
      console.error("Cannot start one-shot recording while another capture is active.");
      return null;
    }

    return new Promise(async (resolve, reject) => {
      const recordedChunks: ArrayBuffer[] = [];
      
      const tempCallbacks: CaptureCallbacks = {
        onChunk: (chunk) => {
          recordedChunks.push(chunk);
        },
        onError: (error) => {
          this.stopCapture();
          reject(error);
        }
      };

      try {
        await this.startCapture(tempCallbacks);

        setTimeout(() => {
          this.stopCapture();
          
          const totalLength = recordedChunks.reduce((acc, chunk) => acc + chunk.byteLength, 0);
          const combined = new Uint8Array(totalLength);
          let offset = 0;
          for (const chunk of recordedChunks) {
            combined.set(new Uint8Array(chunk), offset);
            offset += chunk.byteLength;
          }
          
          resolve(combined.buffer);
        }, durationMs);

      } catch (error) {
        reject(error);
      }
    });
  }


  // ── Public: playback ────────────────────────────────────────────────────────

  /**
   * Initialize the playback pipeline. Call once before the first playChunk().
   * Idempotent — safe to call multiple times.
   */
  async initPlayback(): Promise<void> {
    if (this.playbackState === 'ready') return;
    if (this.playbackState === 'initializing') {
      throw new AudioManagerError(
        'Playback initialization already in progress',
        AudioErrorCode.INVALID_STATE
      );
    }

    this.playbackState = 'initializing';

    try {
      this.playbackCtx = await this.createAudioContext(this.cfg.playbackSampleRate);
      await this.loadWorklet(this.playbackCtx, '/worklets/pcm-playback-processor.js');

      this.playbackNode = new AudioWorkletNode(this.playbackCtx, 'pcm-playback-processor');
      this.playbackNode.connect(this.playbackCtx.destination);
      this.playbackState = 'ready';
    } catch (err) {
      this.playbackState = 'error';
      throw this.wrapError(err);
    }
  }

  /**
   * Feed a Gemini audio response chunk to the playback pipeline.
   * @param chunk  Int16 PCM ArrayBuffer @ 24kHz (ownership is transferred).
   */
  playChunk(chunk: ArrayBuffer): void {
    if (!this.playbackNode || this.playbackState !== 'ready') {
      console.warn('[AudioManager] playChunk ignored — playback not ready');
      return;
    }
    if (!(chunk instanceof ArrayBuffer) || chunk.byteLength === 0) {
      console.warn('[AudioManager] playChunk received empty or invalid buffer');
      return;
    }
    // Transferable: zero-copy hand-off to worklet thread
    this.playbackNode.port.postMessage(chunk, [chunk]);
  }

  // ── Public: resume (handles browser autoplay policy) ───────────────────────

  /**
   * Resume suspended AudioContexts. Call from a user gesture if needed.
   */
  async resumeContexts(): Promise<void> {
    await Promise.allSettled([
      this.captureCtx?.state === 'suspended' ? this.captureCtx.resume() : Promise.resolve(),
      this.playbackCtx?.state === 'suspended' ? this.playbackCtx.resume() : Promise.resolve(),
    ]);
  }

  // ── Public: full teardown ───────────────────────────────────────────────────

  /**
   * Fully destroy all audio resources. Call on session end or unmount.
   */
  async cleanup(): Promise<void> {
    this.stopCapture();
    await this.teardownPlayback();
    this.callbacks = null;
  }

  // ── Public: state getters ───────────────────────────────────────────────────

  get isCapturing(): boolean {
    return this.captureState === 'capturing';
  }

  /** Bypass VAD — send all audio chunks regardless of silence detection */
  setBypassVAD(bypass: boolean): void {
    this._bypassVAD = bypass;
    if (bypass) {
      // Immediately mark as speaking so chunks flow right away
      this.isSpeaking = true;
    }
  }

  get isPlaybackReady(): boolean {
    return this.playbackState === 'ready';
  }

  get currentCaptureState(): CaptureState {
    return this.captureState;
  }

  get currentPlaybackState(): PlaybackState {
    return this.playbackState;
  }

  // ── Private: worklet message handler ────────────────────────────────────────

  private handleCaptureMessage = (event: MessageEvent): void => {
    const buffer = event.data as ArrayBuffer;
    if (!buffer || buffer.byteLength === 0) return;

    const int16 = new Int16Array(buffer);
    
    // Guard against corrupted frames from AudioContext resume glitch
    // (browser suspend/resume side-effects can yield frames of pure zeros)
    let isAllZeros = true;
    for (let i = 0; i < int16.length; i++) {
        if (int16[i] !== 0) {
            isAllZeros = false;
            break;
        }
    }
    if (isAllZeros) return; // Drop it, don't send to Gemini

    // 2. Speech / silence detection
    const speaking = this.isAboveSilenceThreshold(int16);
    this.handleSpeechActivity(speaking);

    // Forward raw PCM to caller if we are in a speech window OR VAD is bypassed.
    // _bypassVAD is set when user is press-and-holding to talk to AI — all audio
    // must flow immediately without waiting for the silence debounce.
    if (this._bypassVAD || this.isSpeaking) {
      this.callbacks?.onChunk(buffer);
    }
  };

  // ── Private: speech / silence ────────────────────────────────────────────────

  private handleSpeechActivity(speaking: boolean): void {
    if (speaking) {
      if (!this.isSpeaking) {
        this.isSpeaking = true;
        this.callbacks?.onSpeech?.();
      }
      this.resetSilenceTimer();
    }
  }

  private resetSilenceTimer(): void {
    if (this.silenceTimer !== null) clearTimeout(this.silenceTimer);
    this.silenceTimer = setTimeout(() => {
      this.isSpeaking = false;
      this.silenceTimer = null;
      this.callbacks?.onSilence?.();
    }, this.cfg.silenceDebounceMs);
  }

  private isAboveSilenceThreshold(samples: Int16Array): boolean {
    let sum = 0;
    for (let i = 0; i < samples.length; i++) {
      sum += samples[i] * samples[i];
    }
    return Math.sqrt(sum / samples.length) > this.cfg.silenceThreshold;
  }

  // ── Private: AudioContext helpers ────────────────────────────────────────────

  private async createAudioContext(sampleRate: number): Promise<AudioContext> {
    const Ctor: typeof AudioContext =
      window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;

    if (!Ctor) {
      throw new AudioManagerError('AudioContext not supported', AudioErrorCode.CONTEXT_CREATION_FAILED);
    }

    const ctx = new Ctor({ sampleRate, latencyHint: 'interactive' });

    // Immediately try to resume (needed if first gesture already fired)
    if (ctx.state === 'suspended') await ctx.resume();

    return ctx;
  }

  private async loadWorklet(ctx: AudioContext, url: string): Promise<void> {
    try {
      await ctx.audioWorklet.addModule(url);
    } catch (err) {
      throw new AudioManagerError(
        `Failed to load worklet: ${url}`,
        AudioErrorCode.WORKLET_LOAD_FAILED,
        err
      );
    }
  }

  private async requestMicrophone(): Promise<MediaStream> {
    try {
      return await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
    } catch (err) {
      throw new AudioManagerError(
        'Microphone access denied or unavailable',
        AudioErrorCode.MIC_ACCESS_DENIED,
        err
      );
    }
  }

  // ── Private: teardown helpers ────────────────────────────────────────────────

  private teardownCapture(): void {
    if (this.silenceTimer !== null) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    this.isSpeaking = false;

    this.captureNode?.disconnect();
    this.captureNode = null;

    this.micStream?.getTracks().forEach(t => t.stop());
    this.micStream = null;

    void this.captureCtx?.close();
    this.captureCtx = null;
  }

  private async teardownPlayback(): Promise<void> {
    this.playbackNode?.disconnect();
    this.playbackNode = null;
    await this.playbackCtx?.close();
    this.playbackCtx = null;
    this.playbackState = 'idle';
  }

  // ── Private: state helpers ───────────────────────────────────────────────────

  private setCaptureState(state: CaptureState): void {
    this.captureState = state;
    this.callbacks?.onStateChange?.(state);
  }

  private wrapError(err: unknown): AudioManagerError {
    if (err instanceof AudioManagerError) return err;
    const message = err instanceof Error ? err.message : String(err);
    return new AudioManagerError(message, AudioErrorCode.CONTEXT_CREATION_FAILED, err);
  }
}

// ─── Pure utility functions ───────────────────────────────────────────────────

function int16ToFloat32(int16: Int16Array): Float32Array {
  const out = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    out[i] = int16[i] / 32768.0;
  }
  return out;
}
