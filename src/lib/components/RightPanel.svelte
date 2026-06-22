<script lang="ts">
  import { onMount } from 'svelte'
  import ToolLog from './ToolLog.svelte'
  import NowPlaying from './NowPlaying.svelte'
  import { tools } from '../stores'
  import { fetchTools } from '../api'

  onMount(async () => {
    try {
      tools.set(await fetchTools())
    } catch {
      /* backend may still be loading */
    }
  })
</script>

<aside class="right">
  <div class="panel block">
    <h2 class="panel-title">Now Playing</h2>
    <NowPlaying />
  </div>
  <div class="panel block grow">
    <h2 class="panel-title">Tool Activity</h2>
    <ToolLog />
  </div>
  <div class="panel block">
    <h2 class="panel-title">Capabilities · {$tools.length}</h2>
    <div class="caps">
      {#each $tools as t}
        <span class="cap" title={t.description}>{t.name}</span>
      {/each}
    </div>
  </div>
</aside>

<style>
  .right { display: flex; flex-direction: column; gap: 16px; padding: 18px; overflow: hidden; }
  .block { padding: 16px; }
  .grow { flex: 1; min-height: 0; display: flex; flex-direction: column; }
  .grow :global(.tools) { flex: 1; }
  .caps { display: flex; flex-wrap: wrap; gap: 6px; }
  .cap {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    color: var(--text-dim);
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 3px 6px;
  }

  @media (max-width: 1100px) {
    .right { overflow: visible; }
    .grow { flex: none; }
    .grow :global(.tools) { max-height: 240px; }
  }
</style>
