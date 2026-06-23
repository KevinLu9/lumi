<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { Play, Pause, SkipBack, SkipForward, Music } from "@lucide/svelte";
  import { nowPlaying, spotifyConfigured } from "../stores";
  import { fetchNowPlaying, spotifyControl } from "../api";

  let timer: ReturnType<typeof setInterval>;
  let busy = false;

  async function poll() {
    try {
      const r = await fetchNowPlaying();
      spotifyConfigured.set(r.configured);
      const { configured, ...np } = r;
      nowPlaying.set(configured ? np : null);
    } catch {
      /* leave last value */
    }
  }

  async function ctrl(action: "play_pause" | "next" | "previous") {
    if (busy) return;
    busy = true;
    try {
      await spotifyControl(action);
      await poll();
    } finally {
      busy = false;
    }
  }

  onMount(() => {
    poll();
    timer = setInterval(poll, 5000);
  });
  onDestroy(() => clearInterval(timer));

  $: np = $nowPlaying;
  $: playing = !!np?.is_playing;
  $: progress = np?.progress_ms ?? 0;
  $: duration = np?.duration_ms ?? 0;
  $: pct = duration > 0 ? Math.min(100, (progress / duration) * 100) : 0;

  function fmt(ms: number) {
    const s = Math.floor(ms / 1000);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }
</script>

{#if !$spotifyConfigured}
  <div class="np off">Spotify not configured</div>
{:else if !np?.track}
  <div class="np-card empty">
    <div class="art placeholder"><Music size={24} strokeWidth={1.6} /></div>
    <div class="meta">
      <div class="track">Nothing playing</div>
      <div class="brand">
        <svg class="logo" viewBox="0 0 168 168" aria-hidden="true"
          ><path
            d="M84 0a84 84 0 1 0 0 168A84 84 0 0 0 84 0Zm38.5 121.2a5.2 5.2 0 0 1-7.2 1.7c-19.6-12-44.3-14.7-73.4-8a5.2 5.2 0 1 1-2.3-10.2c31.8-7.3 59.1-4.2 81.1 9.3a5.2 5.2 0 0 1 1.8 7.2Zm10.3-22.9a6.5 6.5 0 0 1-9 2.1c-22.4-13.8-56.6-17.8-83.1-9.7a6.5 6.5 0 1 1-3.8-12.5c30.3-9.2 68-4.8 93.7 11a6.5 6.5 0 0 1 2.2 9.1Zm.9-23.8C107 58.6 64.2 57.3 39.5 64.8a7.8 7.8 0 1 1-4.5-15c28.4-8.6 75.7-7 105.6 10.8a7.8 7.8 0 1 1-8 13.3Z"
          /></svg
        >Spotify
      </div>
    </div>
  </div>
{:else}
  <div class="np-card">
    {#if np.image}
      <img class="art" src={np.image} alt="Album art" />
    {:else}
      <div class="art placeholder"><Music size={24} strokeWidth={1.6} /></div>
    {/if}
    <div class="meta">
      <div class="track" title={np.track}>{np.track}</div>
      <div class="artist" title={np.artist}>{np.artist}</div>
      <div class="brand">
        <svg class="logo" viewBox="0 0 168 168" aria-hidden="true"
          ><path
            d="M84 0a84 84 0 1 0 0 168A84 84 0 0 0 84 0Zm38.5 121.2a5.2 5.2 0 0 1-7.2 1.7c-19.6-12-44.3-14.7-73.4-8a5.2 5.2 0 1 1-2.3-10.2c31.8-7.3 59.1-4.2 81.1 9.3a5.2 5.2 0 0 1 1.8 7.2Zm10.3-22.9a6.5 6.5 0 0 1-9 2.1c-22.4-13.8-56.6-17.8-83.1-9.7a6.5 6.5 0 1 1-3.8-12.5c30.3-9.2 68-4.8 93.7 11a6.5 6.5 0 0 1 2.2 9.1Zm.9-23.8C107 58.6 64.2 57.3 39.5 64.8a7.8 7.8 0 1 1-4.5-15c28.4-8.6 75.7-7 105.6 10.8a7.8 7.8 0 1 1-8 13.3Z"
          /></svg
        >Spotify
      </div>
    </div>
  </div>
  <div class="progress">
    <span class="time">{fmt(progress)}</span>
    <div class="bar"><div class="fill" style="width: {pct}%"></div></div>
    <span class="time">{fmt(duration)}</span>
  </div>
  <div class="controls">
    <button
      class="ctl"
      title="Previous"
      disabled={busy}
      on:click={() => ctrl("previous")}
    >
      <SkipBack size={18} strokeWidth={2} fill="currentColor" />
    </button>
    <button
      class="ctl play"
      title={playing ? "Pause" : "Play"}
      disabled={busy}
      on:click={() => ctrl("play_pause")}
    >
      {#if playing}
        <Pause size={20} strokeWidth={2} fill="currentColor" />
      {:else}
        <Play size={20} strokeWidth={2} fill="currentColor" />
      {/if}
    </button>
    <button
      class="ctl"
      title="Next"
      disabled={busy}
      on:click={() => ctrl("next")}
    >
      <SkipForward size={18} strokeWidth={2} fill="currentColor" />
    </button>
  </div>
{/if}

<style>
  .np-card {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .art {
    width: 56px;
    height: 56px;
    border-radius: 8px;
    object-fit: cover;
    flex: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  }
  .art.placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.25);
    color: var(--text-dim);
  }
  .meta {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .track {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .artist {
    font-size: 12px;
    color: var(--text-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    letter-spacing: 0.04em;
    color: #1db954;
    margin-top: 2px;
  }
  .logo {
    width: 13px;
    height: 13px;
    fill: #1db954;
  }

  .progress {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
  }
  .time {
    font-size: 10px;
    color: var(--text-dim);
    flex: none;
    min-width: 28px;
  }
  .time:last-child {
    text-align: right;
  }
  .bar {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.12);
    overflow: hidden;
  }
  .fill {
    height: 100%;
    background: #1db954;
    border-radius: 2px;
    transition: width 0.4s linear;
  }

  .controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin-top: 10px;
  }
  .ctl {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    padding: 4px;
    border-radius: 50%;
    transition:
      color 0.15s ease,
      transform 0.1s ease;
  }
  .ctl:hover:not(:disabled) {
    color: var(--text);
  }
  .ctl:active:not(:disabled) {
    transform: scale(0.9);
  }
  .ctl:disabled {
    opacity: 0.4;
    cursor: default;
  }
  .ctl.play {
    width: 38px;
    height: 38px;
    background: #1db954;
    color: #0a0a0a;
  }
  .ctl.play:hover:not(:disabled) {
    background: #1ed760;
    color: #0a0a0a;
  }

  .np {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    line-height: 1.4;
  }
  .off {
    color: var(--text-dim);
    font-size: 12px;
  }
</style>
