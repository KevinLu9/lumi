import { Player } from "./player";
import workletUrl from "./worklet.js?url";

// Owns the /ws/audio WebSocket plus mic capture and TTS playback. Mic frames go up as
// raw float32 buffers; TTS frames come down as int32 sample-rate header + float32 PCM.
export class AudioBridge {
  private ws: WebSocket;
  private player: Player;
  private micCtx: AudioContext | null = null;
  private micStream: MediaStream | null = null;

  constructor() {
    this.player = new Player(() => this.send({ type: "playback_ended" }));
    const proto = location.protocol === "https:" ? "wss" : "ws";
    this.ws = new WebSocket(`${proto}://${location.host}/ws/audio`);
    this.ws.binaryType = "arraybuffer";
    this.ws.onmessage = (e) => this.onMessage(e);
  }

  private onMessage(e: MessageEvent) {
    if (typeof e.data === "string") {
      let msg: any;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      if (msg.type === "flush") this.player.flush();
      else if (msg.type === "chime") this.player.chime();
      return;
    }
    const view = new DataView(e.data as ArrayBuffer);
    const sampleRate = view.getInt32(0, true);
    const samples = new Float32Array((e.data as ArrayBuffer).slice(4));
    this.player.resume();
    this.player.play(sampleRate, samples);
  }

  send(msg: unknown) {
    if (this.ws.readyState === WebSocket.OPEN)
      this.ws.send(JSON.stringify(msg));
  }

  async startMic() {
    if (this.micStream) return;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    const ctx = new AudioContext();
    await ctx.audioWorklet.addModule(workletUrl);
    const src = ctx.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(ctx, "mic-processor");
    node.port.onmessage = (e) => {
      const frame = e.data as Float32Array;
      if (this.ws.readyState === WebSocket.OPEN) this.ws.send(frame.buffer);
    };
    src.connect(node);
    // Some browsers won't pull from a worklet unless it's connected to the graph.
    const muted = ctx.createGain();
    muted.gain.value = 0;
    node.connect(muted);
    muted.connect(ctx.destination);

    this.micCtx = ctx;
    this.micStream = stream;
    this.player.resume();
  }

  stopMic() {
    this.micStream?.getTracks().forEach((t) => t.stop());
    this.micCtx?.close();
    this.micStream = null;
    this.micCtx = null;
  }
}
