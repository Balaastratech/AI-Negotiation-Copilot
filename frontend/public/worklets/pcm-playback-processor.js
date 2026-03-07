/**
 * PCM Playback Processor
 * Runs on dedicated AudioWorklet thread.
 * Receives Int16 PCM chunks from main thread and plays them at 24kHz.
 * Implements a queue with overflow protection to prevent memory leaks.
 */
class PCMPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._queue = [];
    this._maxQueueBytes = 24000 * 2 * 3; // max 3 seconds of audio buffered

    this.port.onmessage = (event) => {
      const totalQueued = this._queue.reduce((sum, buf) => sum + buf.length, 0);
      if (totalQueued * 2 > this._maxQueueBytes) {
        // Drop oldest chunk to prevent unbounded queue growth
        this._queue.shift();
      }
      this._queue.push(new Int16Array(event.data));
    };
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0][0]; // mono channel
    let offset = 0;

    while (offset < output.length && this._queue.length > 0) {
      const chunk = this._queue[0];
      const remaining = output.length - offset;
      const toCopy = Math.min(chunk.length, remaining);

      for (let i = 0; i < toCopy; i++) {
        // Convert Int16 → Float32
        output[offset + i] = chunk[i] / (chunk[i] < 0 ? 0x8000 : 0x7fff);
      }

      if (toCopy === chunk.length) {
        this._queue.shift();
      } else {
        this._queue[0] = chunk.subarray(toCopy);
      }

      offset += toCopy;
    }

    // Fill remaining output with silence if queue is empty
    for (let i = offset; i < output.length; i++) {
      output[i] = 0;
    }

    return true;
  }
}

registerProcessor('pcm-playback-processor', PCMPlaybackProcessor);
