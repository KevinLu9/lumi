<script lang="ts">
  import { onMount } from 'svelte'
  import NowPlaying from './NowPlaying.svelte'
  import { tools, toolModules, activeTools } from '../stores'
  import { fetchTools } from '../api'

  onMount(async () => {
    try {
      const { modules, active } = await fetchTools()
      toolModules.set(modules)
      activeTools.set(new Set(active))
      // Flat list (name + description) powers the "/" command palette in ChatInput.
      tools.set(modules.flatMap((m) => m.tools))
    } catch {
      /* backend may still be loading */
    }
  })

  $: loadedCount = $toolModules
    .flatMap((m) => m.tools)
    .filter((t) => $activeTools.has(t.name)).length

  // Order groups: the default `tools` file first, then modules with any loaded tool,
  // then the rest — alphabetical within each tier. Recomputes as tools get loaded.
  $: sortedModules = [...$toolModules].sort((a, b) => {
    const aActive = a.tools.some((t) => $activeTools.has(t.name))
    const bActive = b.tools.some((t) => $activeTools.has(t.name))
    return (
      Number(b.default) - Number(a.default) ||
      Number(bActive) - Number(aActive) ||
      a.name.localeCompare(b.name)
    )
  })
</script>

<aside class="right">
  <div class="panel block">
    <h2 class="panel-title">Now Playing</h2>
    <NowPlaying />
  </div>
  <div class="panel block grow">
    <h2 class="panel-title">Tools · {loadedCount} loaded</h2>
    <div class="groups">
      {#each sortedModules as m (m.name)}
        <div class="group">
          <div class="gname">
            {m.name}{#if m.default}<span class="tag">default</span>{/if}
          </div>
          <div class="caps">
            {#each m.tools as t}
              <span class="cap" class:active={$activeTools.has(t.name)} title={t.description}>
                {t.name}
              </span>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  </div>
</aside>

<style>
  .right { display: flex; flex-direction: column; gap: 16px; padding: 18px; overflow: hidden; }
  .block { padding: 16px; }
  .grow { flex: 1; min-height: 0; display: flex; flex-direction: column; }
  .groups { display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
  .group { display: flex; flex-direction: column; gap: 6px; }
  .gname {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent);
    font-family: ui-monospace, monospace;
  }
  .tag {
    font-size: 9px;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    padding: 1px 4px;
  }
  .caps { display: flex; flex-wrap: wrap; gap: 6px; }
  .cap {
    font-size: 10px;
    font-family: ui-monospace, monospace;
    color: var(--text-dim);
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 3px 6px;
    opacity: 0.55;
  }
  /* Loaded into the LLM context right now. */
  .cap.active {
    color: var(--text);
    border-color: var(--accent);
    background: rgba(245, 158, 11, 0.12);
    opacity: 1;
  }

  @media (max-width: 1100px) {
    .right { overflow: visible; }
    .grow { flex: none; }
  }
</style>
