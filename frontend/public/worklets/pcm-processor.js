/**
 * PCM Capture Processor
 * Runs on dedicated AudioWorklet thread.
 * Converts Float32 microphone input to Int16 PCM at 16kHz.
 * Sends raw Int16 ArrayBuffer to main thread via postMessage.
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 4096; // ~256ms at 16kHz — balance latency vs. efficiency
  }

  process(inputs, outputs, parameters) {
    if (inputs.length === 0 || inputs[0].length === 0) return true;

    const input = inputs[0][0]; // mono channel, Float32Array (128 samples)

    for (let i = 0; i < input.length; i++) {
      // Convert Float32 [-1.0, 1.0] → Int16 [-32768, 32767]
      const s = Math.max(-1, Math.min(1, input[i]));
      this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7fff);
    }

    if (this._buffer.length >= this._bufferSize) {
      const int16 = new Int16Array(this._buffer.splice(0, this._bufferSize));
      this.port.postMessage(int16.buffer, [int16.buffer]);
    }

    return true; // keep processor alive
  }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
