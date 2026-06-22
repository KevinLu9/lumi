<script lang="ts">
  import { tick } from 'svelte'
  import { sendMessage } from '../api'
  import { micOn, tools, type Tool } from '../stores'

  export let onToggleMic: () => void

  let text = ''
  let inputEl: HTMLInputElement
  let paletteEl: HTMLDivElement
  let selected = 0
  let cursor = 0
  let dismissed = false

  function syncCursor() {
    cursor = inputEl?.selectionStart ?? text.length
  }

  function onInput() {
    dismissed = false // typing re-opens the palette after an Escape
    syncCursor()
  }

  // The active slash token is the text from the "/" nearest before the cursor up to the
  // cursor, with no whitespace in between. This lets the palette trigger anywhere — and
  // chain: e.g. "/get_weather Sydney /get_time" reopens it after the second slash.
  $: query = (() => {
    const before = text.slice(0, cursor)
    const slashIdx = before.lastIndexOf('/')
    if (slashIdx === -1) return null
    const seg = before.slice(slashIdx + 1)
    if (/\s/.test(seg)) return null
    return seg.toLowerCase()
  })()
  $: matches =
    query !== null
      ? $tools.filter(
          (t) =>
            t.name.toLowerCase().includes(query) ||
            t.description.toLowerCase().includes(query),
        )
      : []
  $: showPalette = query !== null && matches.length > 0 && !dismissed
  $: if (selected >= matches.length) selected = 0

  async function choose(tool: Tool) {
    // Replace just the active slash token with /tool_name, keeping the rest of the line.
    const before = text.slice(0, cursor)
    const slashIdx = before.lastIndexOf('/')
    if (slashIdx === -1) return
    const after = text.slice(cursor)
    const token = `/${tool.name} `
    text = before.slice(0, slashIdx) + token + after
    const pos = slashIdx + token.length
    await tick()
    inputEl?.focus()
    inputEl?.setSelectionRange(pos, pos)
    cursor = pos
  }

  async function moveSelection(delta: number) {
    selected = (selected + delta + matches.length) % matches.length
    await tick()
    paletteEl?.querySelector('.opt.sel')?.scrollIntoView({ block: 'nearest' })
  }

  async function submit() {
    const t = text.trim()
    if (!t) return
    text = ''
    await sendMessage(t)
  }

  function onKey(e: KeyboardEvent) {
    if (showPalette) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        moveSelection(1)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        moveSelection(-1)
        return
      }
      if (e.key === 'Tab') {
        e.preventDefault()
        choose(matches[selected])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        dismissed = true
        return
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }
</script>

<div class="input-wrap">
  {#if showPalette}
    <div class="palette panel" bind:this={paletteEl}>
      <div class="palette-hint">Tools · ↑↓ to navigate, ⇥ to insert</div>
      {#each matches as t, i (t.name)}
        <button
          class="opt {i === selected ? 'sel' : ''}"
          on:mousedown|preventDefault={() => choose(t)}
          on:mouseenter={() => (selected = i)}
        >
          <span class="opt-name">/{t.name}</span>
          <span class="opt-desc">{t.description}</span>
        </button>
      {/each}
    </div>
  {/if}

  <div class="input panel">
    <button
      class="mic btn {$micOn ? 'active' : ''}"
      title={$micOn ? 'Mute microphone' : 'Enable microphone'}
      on:click={onToggleMic}
    >
      {$micOn ? '🎙' : '🔇'}
    </button>
    <input
      bind:this={inputEl}
      bind:value={text}
      on:keydown={onKey}
      on:input={onInput}
      on:keyup={syncCursor}
      on:click={syncCursor}
      on:select={syncCursor}
      placeholder="Type to Lumi, / for tools, or speak…"
      autocomplete="off"
    />
    <button class="btn send" on:click={submit}>Send ⏎</button>
  </div>
</div>

<style>
  .input-wrap {
    position: relative;
    width: 100%;
    max-width: 640px;
  }
  .input {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px;
  }
  input {
    flex: 1;
    min-width: 0;
    background: transparent;
    border: none;
    outline: none;
    color: var(--text);
    font-size: 14px;
    padding: 8px;
  }
  .mic { font-size: 16px; padding: 8px 12px; }

  .palette {
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    margin-bottom: 8px;
    padding: 6px;
    max-height: 260px;
    overflow-y: auto;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .palette-hint {
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-dim);
    padding: 6px 8px;
  }
  .opt {
    display: flex;
    flex-direction: column;
    gap: 2px;
    text-align: left;
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    cursor: pointer;
    color: var(--text);
  }
  .opt.sel { background: rgba(251, 146, 60, 0.12); }
  .opt-name { font-family: ui-monospace, monospace; font-size: 13px; color: var(--accent); }
  .opt-desc { font-size: 11px; color: var(--text-dim); }
</style>
