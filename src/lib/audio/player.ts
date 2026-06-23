// Schedules incoming TTS PCM chunks back-to-back through Web Audio, and reports when
// the buffer fully drains so the backend can clear its "speaking" estimate.
export class Player {
  private ctx: AudioContext;
  private nextTime = 0;
  private sources: AudioBufferSourceNode[] = [];
  private onDrained: () => void;

  constructor(onDrained: () => void) {
    this.ctx = new AudioContext();
    this.onDrained = onDrained;
  }

  resume() {
    if (this.ctx.state === "suspended") void this.ctx.resume();
  }

  play(sampleRate: number, samples: Float32Array) {
    const buf = this.ctx.createBuffer(1, samples.length, sampleRate);
    buf.getChannelData(0).set(samples);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.ctx.destination);

    const start = Math.max(this.ctx.currentTime + 0.02, this.nextTime);
    src.start(start);
    this.nextTime = start + buf.duration;
    this.sources.push(src);

    src.onended = () => {
      this.sources = this.sources.filter((s) => s !== src);
      if (this.sources.length === 0) this.onDrained();
    };
  }

  // Drop everything currently scheduled (interrupt / "hold on").
  flush() {
    for (const s of this.sources) {
      try {
        s.onended = null;
        s.stop();
      } catch {
        /* already stopped */
      }
    }
    this.sources = [];
    this.nextTime = 0;
  }

  // Short activation chime, played locally.
  chime() {
    this.resume();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.frequency.value = 880;
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    const t = this.ctx.currentTime;
    gain.gain.setValueAtTime(0.2, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.15);
    osc.start(t);
    osc.stop(t + 0.16);
  }
}
