<script lang="ts">
  import { ArrowUp, ArrowDown, Database, Brain } from "@lucide/svelte";
  import {
    status,
    active,
    connected,
    usageToday,
    currentModel,
  } from "../stores";

  const n = (x: number) => x.toLocaleString();
</script>

<div class="status">
  <div class="line">
    <span class="dot {$connected ? 'on' : 'off'}"></span>
    <span class="k">link</span>
    <span class="v">{$connected ? "connected" : "offline"}</span>
  </div>
  <div class="line">
    <span class="dot {$active ? 'on' : 'idle'}"></span>
    <span class="k">session</span>
    <span class="v">{$active ? "active" : "asleep"}</span>
  </div>
  <div class="line">
    <span class="k">state</span>
    <span class="v big">{$status}</span>
  </div>
  <div class="line usage">
    <span
      class="k"
      title={$currentModel
        ? `Usage today for ${$currentModel.model}`
        : "Usage today"}>today</span
    >
    <div class="tokens">
      <span class="u" title="Input tokens"
        ><ArrowUp size={11} strokeWidth={2} />{n($usageToday.input)}</span
      >
      <span class="u" title="Output tokens"
        ><ArrowDown size={11} strokeWidth={2} />{n($usageToday.output)}</span
      >
      {#if $usageToday.cache_read}
        <span class="u" title="Cache read tokens"
          ><Database size={11} strokeWidth={2} />{n(
            $usageToday.cache_read,
          )}</span
        >
      {/if}
      {#if $usageToday.reasoning}
        <span class="u" title="Reasoning tokens"
          ><Brain size={11} strokeWidth={2} />{n($usageToday.reasoning)}</span
        >
      {/if}
    </div>
  </div>
</div>

<style>
  .status {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .line {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }
  .k {
    color: var(--text-dim);
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    min-width: 58px;
  }
  .v {
    color: var(--text);
  }
  .v.big {
    font-size: 15px;
    color: var(--accent);
    letter-spacing: 0.08em;
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--text-dim);
  }
  .dot.on {
    background: var(--ok);
    box-shadow: 0 0 8px var(--ok);
  }
  .dot.idle {
    background: var(--warn);
  }
  .dot.off {
    background: #6b7280;
  }
  .usage {
    align-items: flex-start;
  }
  .tokens {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 11px;
    font-family: ui-monospace, monospace;
    color: var(--text-dim);
  }
  .tokens .u {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    cursor: default;
  }
  .tokens :global(svg) {
    opacity: 0.85;
    flex: none;
  }
</style>
