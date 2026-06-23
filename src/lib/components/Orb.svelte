<script lang="ts">
  import { audioLevel, type Status } from "../stores";
  export let status: Status = "idle";

  const labels: Record<Status, string> = {
    idle: "say 'hey lumi'",
    listening: "listening",
    recording: "recording",
    transcribing: "transcribing",
    thinking: "thinking",
    speaking: "speaking",
  };
</script>

<div class="orb-wrap" style="--level:{$audioLevel}">
  <div class="rings status-{status}">
    <span class="ring r1"></span>
    <span class="ring r2"></span>
    <span class="ring r3"></span>
    <div class="orb">
      <div class="glow"></div>
      <div class="core"></div>
      <div class="plasma"></div>
      <div class="rim"></div>
      <div class="sweep"></div>
    </div>
  </div>
  <div class="label">{labels[status]}</div>
</div>

<style>
  .orb-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
    user-select: none;
  }

  .rings {
    position: relative;
    width: 300px;
    height: 300px;
    display: grid;
    place-items: center;
  }

  .orb {
    position: relative;
    width: 170px;
    height: 170px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    /* Audio-reactive layer (#8): the whole orb swells and its halo brightens
       with the live amplitude. No animation lives on .orb, so these compose
       cleanly with the breathing/plasma animations on the children. */
    transform: scale(calc(1 + var(--level, 0) * 0.09));
    filter: drop-shadow(
      0 0 calc(10px + var(--level, 0) * 55px) var(--accent-glow)
    );
    transition:
      transform 0.07s ease-out,
      filter 0.12s ease-out;
  }
  .orb > * {
    position: absolute;
    inset: 0;
    border-radius: 50%;
  }

  .core {
    z-index: 1;
    background: radial-gradient(
      circle at 35% 30%,
      #fff1e0 0%,
      var(--accent) 32%,
      #9a3412 78%,
      #3a1505 100%
    );
    box-shadow:
      inset 0 0 40px rgba(255, 255, 255, 0.35),
      0 0 60px var(--accent-glow),
      0 0 120px rgba(154, 52, 18, 0.5);
    animation: breathe 4s ease-in-out infinite;
  }

  /* Plasma core (#3): three offset radial blobs that slowly rotate and drift,
     blended additively so the inside churns like contained energy. */
  .plasma {
    z-index: 2;
    background:
      radial-gradient(
        circle at 30% 32%,
        rgba(255, 214, 150, 0.55),
        transparent 46%
      ),
      radial-gradient(
        circle at 72% 60%,
        rgba(255, 120, 40, 0.5),
        transparent 50%
      ),
      radial-gradient(
        circle at 48% 78%,
        rgba(154, 52, 18, 0.6),
        transparent 56%
      );
    mix-blend-mode: screen;
    filter: blur(5px);
    animation: plasma 9s ease-in-out infinite alternate;
  }

  /* Fresnel rim (#2): bright glassy edge that falls off toward the centre, so
     the sphere reads as lit glass rather than a flat disc. */
  .rim {
    z-index: 3;
    background: radial-gradient(
      circle at 50% 50%,
      transparent 56%,
      rgba(255, 224, 178, 0.3) 80%,
      rgba(255, 186, 120, 0.65) 93%,
      transparent 100%
    );
    mix-blend-mode: screen;
    pointer-events: none;
  }

  /* Conic energy sweep (#1): a bright arc orbiting in a thin ring band, like a
     reactor scan line. Masked to a hairline annulus just outside the core. */
  .sweep {
    z-index: 4;
    inset: -7px;
    background: conic-gradient(
      from 0deg,
      transparent 0deg,
      transparent 295deg,
      rgba(255, 200, 120, 0.15) 330deg,
      var(--accent) 352deg,
      #fff 360deg
    );
    -webkit-mask: radial-gradient(
      circle,
      transparent 66%,
      #000 69%,
      #000 73%,
      transparent 76%
    );
    mask: radial-gradient(
      circle,
      transparent 66%,
      #000 69%,
      #000 73%,
      transparent 76%
    );
    opacity: 0.85;
    animation: spin 6s linear infinite;
  }

  .glow {
    z-index: 0;
    inset: -30px;
    background: radial-gradient(circle, var(--accent-glow) 0%, transparent 60%);
    filter: blur(12px);
    opacity: 0.5;
    animation: breathe 4s ease-in-out infinite;
  }

  .ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(251, 146, 60, 0.25);
    /* Rings glow outward with the live audio level (#8). box-shadow is safe to
       drive here even when a ring is mid spin/ripple animation. */
    box-shadow: 0 0 calc(var(--level, 0) * 22px) rgba(251, 146, 60, 0.55);
  }
  .r1 {
    width: 210px;
    height: 210px;
  }
  .r2 {
    width: 255px;
    height: 255px;
    border-color: rgba(245, 158, 11, 0.18);
  }
  .r3 {
    width: 300px;
    height: 300px;
    border-color: rgba(255, 170, 90, 0.12);
  }

  .label {
    font-size: 13px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--text-dim);
  }

  @keyframes breathe {
    0%,
    100% {
      transform: scale(0.96);
      opacity: 0.85;
    }
    50% {
      transform: scale(1.04);
      opacity: 1;
    }
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @keyframes plasma {
    0% {
      transform: rotate(0deg) scale(1);
      opacity: 0.85;
    }
    50% {
      opacity: 1;
    }
    100% {
      transform: rotate(38deg) scale(1.12);
      opacity: 0.9;
    }
  }
  @keyframes ripple {
    0% {
      transform: scale(0.7);
      opacity: 0.7;
    }
    100% {
      transform: scale(1.25);
      opacity: 0;
    }
  }

  /* ---- state reactions ---- */

  .status-idle .core,
  .status-idle .glow {
    animation-duration: 7s;
    opacity: 0.7;
  }
  .status-idle .sweep {
    animation-duration: 9s;
    opacity: 0.6;
  }
  .status-idle .plasma {
    animation-duration: 13s;
  }

  .status-listening .ring {
    border-color: rgba(251, 146, 60, 0.45);
  }
  .status-listening .core {
    animation-duration: 3s;
  }

  .status-recording .r1,
  .status-recording .r2 {
    animation: ripple 1.4s ease-out infinite;
    border-color: var(--accent);
  }
  .status-recording .r2 {
    animation-delay: 0.5s;
  }

  .status-transcribing .r1 {
    border-top-color: var(--accent);
    border-right-color: var(--accent);
    animation: spin 1.1s linear infinite;
  }

  @media (max-width: 700px) {
    .rings {
      width: 220px;
      height: 220px;
    }
    .orb {
      width: 124px;
      height: 124px;
    }
    .r1 {
      width: 154px;
      height: 154px;
    }
    .r2 {
      width: 187px;
      height: 187px;
    }
    .r3 {
      width: 220px;
      height: 220px;
    }
    .orb-wrap {
      gap: 20px;
    }
  }

  .rings.status-thinking {
    filter: hue-rotate(-18deg);
  }
  .status-thinking .r1 {
    border-top-color: var(--accent2);
    animation: spin 0.8s linear infinite;
  }
  .status-thinking .r2 {
    border-bottom-color: var(--accent);
    animation: spin 1.4s linear infinite reverse;
  }
  .status-thinking .core {
    animation-duration: 1.4s;
  }
  .status-thinking .sweep {
    animation-duration: 1.8s;
    opacity: 1;
  }
  .status-thinking .plasma {
    animation-duration: 4s;
  }

  .status-speaking .core {
    background: radial-gradient(
      circle at 35% 30%,
      #ffe6c2 0%,
      var(--accent2) 34%,
      #9a3412 80%,
      #3a1505 100%
    );
    animation: breathe 0.6s ease-in-out infinite;
    box-shadow:
      inset 0 0 40px rgba(255, 255, 255, 0.4),
      0 0 70px var(--accent2-glow),
      0 0 140px rgba(245, 158, 11, 0.5);
  }
  .status-speaking .glow {
    background: radial-gradient(
      circle,
      var(--accent2-glow) 0%,
      transparent 60%
    );
    animation: breathe 0.6s ease-in-out infinite;
  }
  .status-speaking .ring {
    border-color: rgba(245, 158, 11, 0.4);
  }
  .status-speaking .sweep {
    animation-duration: 1.4s;
    opacity: 1;
  }
  .status-speaking .plasma {
    animation-duration: 3.5s;
    filter: blur(4px) brightness(1.15);
  }
</style>
