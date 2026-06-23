<script lang="ts">
  import type { Status } from "../stores";
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

<div class="orb-wrap">
  <div class="rings status-{status}">
    <span class="ring r1"></span>
    <span class="ring r2"></span>
    <span class="ring r3"></span>
    <div class="orb">
      <div class="core"></div>
      <div class="glow"></div>
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
  }

  .core {
    width: 100%;
    height: 100%;
    border-radius: 50%;
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

  .glow {
    position: absolute;
    inset: -30px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--accent-glow) 0%, transparent 60%);
    filter: blur(12px);
    opacity: 0.5;
    animation: breathe 4s ease-in-out infinite;
  }

  .ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(251, 146, 60, 0.25);
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
</style>
