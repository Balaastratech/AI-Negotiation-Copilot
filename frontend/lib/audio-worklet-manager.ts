import { VoiceFingerprint, identifySpeakerWithConfidence } from './voice-fingerprint';

// ─── Types ────────────────────────────────────────────────────────────────────

export type Speaker = 'USER' | 'COUNTERPARTY';

export type CaptureState = 'idle' | 'starting' | 'capturing' | 'stopping' | 'error';
export type PlaybackState = 'idle' | 'initializing' | 'ready' | 'error';

export interface AudioManagerConfig {
  /** RMS threshold for speech detection. Default: 500 */
  silenceThreshold?: number;
  /** Milliseconds of silence before firing onSilence. Default: 500 */
  silenceDebounceMs?: number;
  /** Minimum confidence to accept a speaker ID result. Default: 0.85 */
  minSpeakerConfidence?: number;
  /** Number of past frames to use for majority-vote smoothing. Default: 3 */
  smoothingWindow?: number;
  /** Minimum Float32 samples accumulated before running speaker ID. Default: 8000 */
  speakerIdChunkSize?: number;
  /** Sample rate for capture. Default: 16000 */
  captureSampleRate?: number;
  /** Sample rate for playback (Gemini output). Default: 24000 */
  playbackSampleRate?: number;
}

export interface SpeakerIdentificationResult {
  speaker: Speaker;
  confidence: number;
  audioChunk: Float32Array;
}

export interface CaptureCallbacks {
  onChunk: (buffer: ArrayBuffer) => void;
  onSilence?: () => void;
  onSpeech?: () => void;
  onSpeakerIdentified?: (result: SpeakerIdentificationResult) => void;
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

// ─── Speaker ID: sliding window majority vote ─────────────────────────────────

class SpeakerSmoother {
  private history: Speaker[] = [];

  constructor(
    private readonly windowSize: number,
    private readonly minConfidence: number
  ) { }

  /** Feed a new raw result; returns the smoothed speaker. */
  update(speaker: Speaker, confidence: number): Speaker | null {
    if (confidence < this.minConfidence) return null; // reject low-confidence

    this.history.push(speaker);
    if (this.history.length > this.windowSize) this.history.shift();

    const userVotes = this.history.filter(s => s === 'USER').length;
    return userVotes > this.windowSize / 2 ? 'USER' : 'COUNTERPARTY';
  }

  reset(): void {
    this.history = [];
  }
}

// ─── AudioWorkletManager ──────────────────────────────────────────────────────

/**
 * AudioWorkletManager
 *
 * Manages microphone capture and audio playback for the Gemini Live API.
 * - Capture outputs Int16 PCM @ 16kHz (raw ArrayBuffers, no base64).
 * - Playback expects Int16 PCM @ 24kHz ArrayBuffers from Gemini.
 * - Optional real-time speaker identification via VoiceFingerprint.
 *
 * Lifecycle:
 *   1. new AudioWorkletManager(config?)
 *   2. setVoiceprint(vp)          — optional, enables speaker ID
 *   3. await startCapture(cbs)    — starts mic
 *   4. await initPlayback()       — prepares playback pipeline
 *   5. playChunk(buffer)          — feed Gemini audio
 *   6. stopCapture()              — mic off, playback stays alive
 *   7. cleanup()                  — full teardown
 */
export class AudioWorkletManager {
  // ── Config ──────────────────────────────────────────────────────────────────

  private readonly cfg: Required<AudioManagerConfig> = {
    silenceThreshold: 50,
    silenceDebounceMs: 500,
    minSpeakerConfidence: 0.85,
    smoothingWindow: 3,
    speakerIdChunkSize: 8000,
    captureSampleRate: 16000,
    playbackSampleRate: 24000,
  };

  // ── State ───────────────────────────────────────────────────────────────────

  private captureState: CaptureState = 'idle';
  private playbackState: PlaybackState = 'idle';

  // ── Capture resources ───────────────────────────────────────────────────────

  private captureCtx: AudioContext | null = null;
  private captureNode: AudioWorkletNode | null = null;
  private micStream: MediaStream | null = null;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;
  private isSpeaking = false;

  // ── Playback resources ──────────────────────────────────────────────────────

  private playbackCtx: AudioContext | null = null;
  private playbackNode: AudioWorkletNode | null = null;

  // ── Speaker identification ──────────────────────────────────────────────────

  private voiceprint: VoiceFingerprint | null = null;
  private speakerBuffer: Float32Array[] = [];
  private smoother: SpeakerSmoother;
  private lastKnownSpeaker: Speaker | null = null;

  // ── Callbacks ───────────────────────────────────────────────────────────────

  private callbacks: CaptureCallbacks | null = null;

  // ────────────────────────────────────────────────────────────────────────────

  constructor(config: AudioManagerConfig = {}) {
    Object.assign(this.cfg, config);
    this.smoother = new SpeakerSmoother(
      this.cfg.smoothingWindow,
      this.cfg.minSpeakerConfidence
    );
  }

  // ── Public: voiceprint ──────────────────────────────────────────────────────

  /**
   * Load a pre-enrolled VoiceFingerprint to enable speaker identification.
   * Call before or during an active capture session.
   */
  setVoiceprint(vp: VoiceFingerprint): void {
    this.voiceprint = vp;
    this.smoother.reset();
    this.lastKnownSpeaker = null;
    console.debug('[AudioManager] Voiceprint loaded', {
      coefficients: vp.numCoefficients,
      enrollmentDuration: vp.enrollmentDuration,
      sampleRate: vp.sampleRate,
    });
  }

  clearVoiceprint(): void {
    this.voiceprint = null;
    this.speakerBuffer = [];
    this.smoother.reset();
    this.lastKnownSpeaker = null;
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
    this.clearVoiceprint();
  }

  // ── Public: state getters ───────────────────────────────────────────────────

  get isCapturing(): boolean {
    return this.captureState === 'capturing';
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

    // 1. Forward raw PCM to caller ONLY if we are currently in a speech window
    // (This prevents sending continuous background noise which causes Gemini to buffer >20s and crash with 1007)
    if (this.isSpeaking) {
      this.callbacks?.onChunk(buffer);
    }

    // 3. Speaker identification (if voiceprint loaded)
    if (this.voiceprint && this.callbacks?.onSpeakerIdentified && speaking) {
      this.processSpeakerIdentification(int16);
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

  // ── Private: speaker identification ─────────────────────────────────────────

  private processSpeakerIdentification(int16: Int16Array): void {
    // Convert Int16 → Float32 (normalized)
    const float32 = int16ToFloat32(int16);
    this.speakerBuffer.push(float32);

    const totalSamples = this.speakerBuffer.reduce((n, c) => n + c.length, 0);
    if (totalSamples < this.cfg.speakerIdChunkSize) return;

    // Concatenate accumulated frames
    const combined = concatFloat32(this.speakerBuffer, totalSamples);

    // Run identification
    const raw = identifySpeakerWithConfidence(combined, this.voiceprint!);

    // Majority-vote smoothing
    const smoothed = this.smoother.update(raw.speaker, raw.confidence);
    const resolved: Speaker = smoothed ?? this.lastKnownSpeaker ?? raw.speaker;

    if (smoothed !== null) this.lastKnownSpeaker = smoothed;

    this.callbacks?.onSpeakerIdentified?.({
      speaker: resolved,
      confidence: raw.confidence,
      audioChunk: combined,
    });

    // Retain the last frame for temporal overlap (improves continuity)
    this.speakerBuffer = [this.speakerBuffer[this.speakerBuffer.length - 1]];
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
    this.speakerBuffer = [];

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

function concatFloat32(chunks: Float32Array[], totalLength: number): Float32Array {
  const out = new Float32Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}
