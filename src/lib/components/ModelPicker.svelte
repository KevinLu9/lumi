<script lang="ts">
  import { onMount } from "svelte";
  import { Cpu } from "@lucide/svelte";
  import { models, currentModel } from "../stores";
  import { fetchModels, setModel } from "../api";

  let switching = false;
  let error = "";

  // value encodes provider+model so the <select> can round-trip both fields.
  const key = (provider: string, model: string) => `${provider}::${model}`;
  $: selected = $currentModel
    ? key($currentModel.provider, $currentModel.model)
    : "";

  onMount(async () => {
    try {
      const { current, models: list } = await fetchModels();
      models.set(list);
      currentModel.set(current);
    } catch {
      /* backend may still be loading */
    }
  });

  async function onChange(e: Event) {
    const val = (e.target as HTMLSelectElement).value;
    const [provider, model] = val.split("::");
    if (!provider || !model) return;
    error = "";
    switching = true;
    try {
      const r = await setModel(provider, model);
      if (!r.ok) error = r.error || "Could not switch model.";
      else if (r.current) currentModel.set(r.current);
    } catch {
      error = "Request failed.";
    } finally {
      switching = false;
    }
  }
</script>

<div class="picker">
  <span class="ico"><Cpu size={13} strokeWidth={2} /></span>
  <select
    class="sel"
    value={selected}
    on:change={onChange}
    disabled={switching || $models.length === 0}
  >
    {#each $models as m}
      <option value={key(m.provider, m.model)}>
        {m.label || m.model} ({m.provider})
      </option>
    {/each}
  </select>
</div>
{#if error}<div class="err">{error}</div>{/if}

<style>
  .picker {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .ico {
    color: var(--accent);
    flex: none;
    display: inline-flex;
  }
  .sel {
    flex: 1;
    min-width: 0;
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    padding: 7px 9px;
    color: var(--text);
    font-size: 12px;
    outline: none;
    cursor: pointer;
  }
  .sel:focus {
    border-color: var(--accent);
  }
  .sel:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .err {
    color: #f87171;
    font-size: 11px;
    margin-top: 6px;
  }
</style>
