<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { nowPlaying, spotifyConfigured } from '../stores'
  import { fetchNowPlaying } from '../api'

  let timer: ReturnType<typeof setInterval>

  async function poll() {
    try {
      const r = await fetchNowPlaying()
      spotifyConfigured.set(r.configured)
      nowPlaying.set(r.track)
    } catch {
      /* leave last value */
    }
  }

  onMount(() => {
    poll()
    timer = setInterval(poll, 5000)
  })
  onDestroy(() => clearInterval(timer))
</script>

{#if $spotifyConfigured}
  <div class="np">
    <span class="icon">♪</span>
    <span class="track">{$nowPlaying ?? 'Nothing playing'}</span>
  </div>
{:else}
  <div class="np off">Spotify not configured</div>
{/if}

<style>
  .np { display: flex; align-items: center; gap: 10px; font-size: 13px; line-height: 1.4; }
  .icon { color: var(--accent2); font-size: 16px; }
  .track { color: var(--text); }
  .off { color: var(--text-dim); font-size: 12px; }
</style>
