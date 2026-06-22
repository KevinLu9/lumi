<script lang="ts">
  import { afterUpdate } from 'svelte'
  import { transcript } from '../stores'

  let el: HTMLDivElement

  // Split out <silent> blocks so spoken vs on-screen-only content reads differently.
  function parts(text: string) {
    const out: { silent: boolean; text: string }[] = []
    const re = /<silent>([\s\S]*?)<\/silent>/g
    let last = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(text))) {
      if (m.index > last) out.push({ silent: false, text: text.slice(last, m.index) })
      out.push({ silent: true, text: m[1] })
      last = re.lastIndex
    }
    if (last < text.length) out.push({ silent: false, text: text.slice(last) })
    return out.filter((p) => p.text.trim())
  }

  afterUpdate(() => {
    if (el) el.scrollTop = el.scrollHeight
  })
</script>

<div class="log" bind:this={el}>
  {#each $transcript as item}
    {#if item.role === 'system'}
      <div class="divider"><span>{item.text}</span></div>
    {:else}
      <div class="row {item.role}">
        <span class="who">{item.role === 'user' ? 'You' : 'Lumi'}</span>
        <div class="bubble">
          {#each parts(item.text) as p}
            {#if p.silent}
              <pre class="silent">{p.text.trim()}</pre>
            {:else}
              <span>{p.text}</span>
            {/if}
          {/each}
        </div>
      </div>
    {/if}
  {/each}
  {#if $transcript.length === 0}
    <div class="empty">No conversation yet — say “hey lumi” or type below.</div>
  {/if}
</div>

<style>
  .log {
    width: 100%;
    max-width: 640px;
    max-height: 32vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 4px 8px;
  }
  .row { display: flex; flex-direction: column; gap: 4px; }
  .row.user { align-items: flex-end; }
  .who {
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--text-dim);
  }
  .bubble {
    max-width: 85%;
    padding: 10px 14px;
    border-radius: 14px;
    font-size: 14px;
    line-height: 1.5;
    border: 1px solid var(--panel-border);
  }
  .row.user .bubble {
    background: rgba(251, 146, 60, 0.1);
    border-color: rgba(251, 146, 60, 0.3);
  }
  .row.lumi .bubble {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.25);
  }
  .silent {
    margin: 6px 0 0;
    padding: 8px 10px;
    background: rgba(0, 0, 0, 0.35);
    border-radius: 8px;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text-dim);
  }
  .empty { color: var(--text-dim); font-size: 13px; text-align: center; padding: 20px; }
  .divider {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--text-dim);
    font-size: 10px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    margin: 4px 0;
  }
  .divider span {
    padding: 0 12px;
    border-top: 1px solid var(--panel-border);
    border-bottom: 1px solid var(--panel-border);
    line-height: 22px;
    border-radius: 6px;
  }
</style>
