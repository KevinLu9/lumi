<script lang="ts">
  import { toolCalls } from '../stores'

  function fmtArgs(args: Record<string, unknown>) {
    const entries = Object.entries(args)
    if (!entries.length) return ''
    return entries.map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(', ')
  }
</script>

<div class="tools">
  {#each $toolCalls as call (call.ts + call.name)}
    <div class="call">
      <div class="head">
        <span class="check">✓</span>
        <span class="name">{call.name}</span>
      </div>
      {#if fmtArgs(call.args)}
        <div class="args">{fmtArgs(call.args)}</div>
      {/if}
      <div class="result">{call.result}</div>
    </div>
  {/each}
  {#if $toolCalls.length === 0}
    <div class="empty">No tool activity yet.</div>
  {/if}
</div>

<style>
  .tools { display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
  .call {
    border-left: 2px solid var(--accent);
    padding: 4px 0 4px 10px;
  }
  .head { display: flex; align-items: center; gap: 6px; }
  .check { color: var(--ok); font-size: 12px; }
  .name { font-size: 13px; color: var(--text); font-family: ui-monospace, monospace; }
  .args { font-size: 11px; color: var(--text-dim); margin-top: 2px; word-break: break-word; }
  .result {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 3px;
    opacity: 0.85;
    max-height: 48px;
    overflow: hidden;
  }
  .empty { color: var(--text-dim); font-size: 12px; }
</style>
