/**
 * PCM Capture Processor
 * Runs on dedicated AudioWorklet thread.
 * Converts Float32 microphone input to Int16 PCM at 16kHz via decimation.
 * Sends raw Int16 ArrayBuffer to main thread via postMessage.
 *
 * RESAMPLER NOTE:
 * We use integer-based Bresenham-style accumulation (phase stepping with
 * numerator/denominator) instead of a float accumulator.  A pure-float
 * accumulator (accumulator += 1; if (acc >= ratio) acc -= ratio) accumulates
 * IEEE-754 rounding error that grows linearly with time.  After ~2000 chunks
 * (≈3 min) the output sample rate deviates enough from 16 kHz that Gemini
 * rejects the stream with error 1007.
 *
 * The integer phase stepper is exact and drift-free for any rational ratio.
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 1600;        // 100 ms at 16 kHz
    this._targetSampleRate = 16000;

    // Integer phase accumulator for drift-free resampling
    // Phase advances by _targetSampleRate each input sample.
    // We emit one output sample and subtract _inputSampleRate whenever phase >= _inputSampleRate.
    // (equivalent to Bresenham / GCD-safe rational resampling)
    this._phase = 0;
    // _inputSampleRate is set on first process() call from the global `sampleRate`
    this._inputSampleRate = 0;

    this.port.onmessage = (event) => {
      if (event.data === 'flush' && this._buffer.length > 0) {
        const samples = this._buffer;
        this._buffer = [];
        this._postInt16(samples);
      }
    };
  }

  /** Convert plain-number array to Int16 LE ArrayBuffer and postMessage it. */
  _postInt16(samples) {
    const ab = new ArrayBuffer(samples.length * 2);
    const dv = new DataView(ab);
    for (let i = 0; i < samples.length; i++) {
      dv.setInt16(i * 2, samples[i], /* littleEndian= */ true);
    }
    this.port.postMessage(ab, [ab]);
  }

  process(inputs /*, outputs, parameters */) {
    const input = inputs[0]?.[0];
    if (!input || input.length === 0) return true;

    // Latch the real AudioContext sample rate on first call.
    // The browser may silently ignore the requested 16000 Hz and use e.g. 44100 or 48000.
    if (this._inputSampleRate === 0) {
      this._inputSampleRate = sampleRate; // global provided by AudioWorkletGlobalScope
    }

    const inRate = this._inputSampleRate;
    const outRate = this._targetSampleRate;

    for (let i = 0; i < input.length; i++) {
      // Advance phase by output rate (integer steps → zero drift)
      this._phase += outRate;

      if (this._phase >= inRate) {
        this._phase -= inRate;

        // Clamp Float32 [-1, 1] → Int16 [-32768, 32767]
        const s = Math.max(-1, Math.min(1, input[i]));
        this._buffer.push(s < 0 ? (s * 0x8000) | 0 : (s * 0x7fff) | 0);
      }
    }

    // Flush when we have a full 100 ms chunk
    while (this._buffer.length >= this._bufferSize) {
      const samples = this._buffer.splice(0, this._bufferSize);
      this._postInt16(samples);
    }

    return true; // keep processor alive
  }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
