/**
 * PCM Capture Processor
 * Runs on dedicated AudioWorklet thread.
 * Converts Float32 microphone input to Int16 PCM at 16kHz via decimation.
 * Sends raw Int16 ArrayBuffer to main thread via postMessage.
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 1600;  // 100ms at 16kHz - optimal balance
    this._targetSampleRate = 16000;
    this._resampleAccumulator = 0;
    
    this.port.onmessage = (event) => {
      if (event.data === 'flush' && this._buffer.length > 0) {
        const samples = this._buffer;
        this._buffer = [];
        
        // Use DataView to ensure little-endian encoding
        const arrayBuffer = new ArrayBuffer(samples.length * 2);
        const dataView = new DataView(arrayBuffer);
        
        for (let i = 0; i < samples.length; i++) {
          dataView.setInt16(i * 2, samples[i], true); // true = little-endian
        }
        
        this.port.postMessage(arrayBuffer, [arrayBuffer]);
      }
    };
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0]?.[0];
    if (!input || input.length === 0) return true;

    const ratio = sampleRate / this._targetSampleRate;

    for (let i = 0; i < input.length; i++) {
        this._resampleAccumulator += 1;
        
        if (this._resampleAccumulator >= ratio) {
            this._resampleAccumulator -= ratio;
            
            // Convert Float32 [-1.0, 1.0] → Int16 [-32768, 32767]
            const s = Math.max(-1, Math.min(1, input[i]));
            this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7fff);
        }
    }

    if (this._buffer.length >= this._bufferSize) {
      const samples = this._buffer.splice(0, this._bufferSize);
      
      // Use DataView to ensure little-endian encoding
      // This guarantees the format matches what Gemini expects: s16le (signed 16-bit little-endian)
      const arrayBuffer = new ArrayBuffer(samples.length * 2);
      const dataView = new DataView(arrayBuffer);
      
      for (let i = 0; i < samples.length; i++) {
        // Explicitly write as little-endian Int16
        // Second parameter (true) forces little-endian byte order
        dataView.setInt16(i * 2, samples[i], true);
      }
      
      this.port.postMessage(arrayBuffer, [arrayBuffer]);
    }

    return true; // keep processor alive
  }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
