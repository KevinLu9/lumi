<script lang="ts">
  import { afterUpdate, type Component } from 'svelte'
  import { ArrowUp, ArrowDown, Database, Brain } from '@lucide/svelte'
  import WeatherWidget from './WeatherWidget.svelte'
  import { transcript, type Usage } from '../stores'

  let el: HTMLDivElement

  // Show only the token counts that apply (cache write/read & reasoning are provider- and
  // model-dependent, so they're often 0).
  type UsagePart = { icon: Component; text: string; title: string }
  function usageParts(u: Usage): UsagePart[] {
    const n = (x: number) => x.toLocaleString()
    const parts: UsagePart[] = [
      { icon: ArrowUp, text: n(u.input), title: 'Input tokens' },
      { icon: ArrowDown, text: n(u.output), title: 'Output tokens' },
    ]
    if (u.cache_read) parts.push({ icon: Database, text: `${n(u.cache_read)} read`, title: 'Cache read tokens' })
    if (u.cache_write) parts.push({ icon: Database, text: `${n(u.cache_write)} write`, title: 'Cache write tokens' })
    if (u.reasoning) parts.push({ icon: Brain, text: n(u.reasoning), title: 'Reasoning tokens' })
    return parts
  }

  function fmtArgs(args: Record<string, unknown>) {
    const entries = Object.entries(args)
    if (!entries.length) return ''
    return entries.map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(', ')
  }

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
    {#if item.role === 'weather'}
      <WeatherWidget location={item.location} days={item.days} />
    {:else if item.role === 'tool'}
      <details class="tool">
        <summary>
          <span class="chev">▸</span>
          <span class="tname">{item.name}</span>
          {#if fmtArgs(item.args)}<span class="targs">{fmtArgs(item.args)}</span>{/if}
        </summary>
        <div class="tresult">{item.result || '(no output)'}</div>
      </details>
    {:else if item.role === 'system'}
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
        {#if item.role === 'lumi' && item.usage}
          <div class="usage">
            {#each usageParts(item.usage) as part}
              {@const Icon = part.icon}
              <span class="u" title={part.title}><Icon size={11} strokeWidth={2} />{part.text}</span>
            {/each}
          </div>
        {/if}
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
  .tool {
    align-self: flex-start;
    max-width: 85%;
    border-left: 2px solid var(--accent);
    background: rgba(245, 158, 11, 0.05);
    border-radius: 0 8px 8px 0;
  }
  .tool summary {
    display: flex;
    align-items: baseline;
    gap: 7px;
    padding: 6px 12px;
    cursor: pointer;
    list-style: none;
    font-size: 12px;
    line-height: 1.4;
  }
  .tool summary::-webkit-details-marker { display: none; }
  .chev {
    color: var(--accent);
    font-size: 10px;
    transition: transform 0.15s ease;
    flex: none;
  }
  .tool[open] .chev { transform: rotate(90deg); }
  .tname { color: var(--text); font-family: ui-monospace, monospace; flex: none; }
  .targs {
    color: var(--text-dim);
    font-family: ui-monospace, monospace;
    word-break: break-word;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tresult {
    padding: 0 12px 8px 26px;
    font-size: 12px;
    color: var(--text-dim);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .usage {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 10px;
    font-family: ui-monospace, monospace;
    color: var(--text-dim);
    opacity: 0.7;
    padding: 0 4px;
  }
  .usage .u { display: inline-flex; align-items: center; gap: 3px; cursor: default; }
  .usage :global(svg) { opacity: 0.85; flex: none; }
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
