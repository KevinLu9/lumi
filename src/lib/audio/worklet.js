// AudioWorklet that downsamples the mic to 16kHz mono and emits 512-sample float32
// frames — matching the backend transcriber's BLOCK_SAMPLES / SAMPLE_RATE.
class MicProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.targetRate = 16000
    this.ratio = sampleRate / this.targetRate // `sampleRate` is global in worklet scope
    this.frameSize = 512
    this.buf = new Float32Array(this.frameSize)
    this.count = 0
    this.acc = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0]) return true
    const ch = input[0]
    for (let i = 0; i < ch.length; i++) {
      this.acc += 1
      if (this.acc >= this.ratio) {
        this.acc -= this.ratio
        this.buf[this.count++] = ch[i]
        if (this.count === this.frameSize) {
          this.port.postMessage(this.buf.slice(0))
          this.count = 0
        }
      }
    }
    return true
  }
}

registerProcessor('mic-processor', MicProcessor)
