<script lang="ts">
  import { sendMessage } from '../api'
  import { micOn, tools, type Tool } from '../stores'

  export let onToggleMic: () => void

  let text = ''
  let inputEl: HTMLInputElement
  let selected = 0

  // Natural-language starters for known tools; falls back to the tool description.
  const TEMPLATES: Record<string, string> = {
    get_time: 'What time is it?',
    get_weather: "What's the weather in ",
    calculate: 'Calculate ',
    set_timer: 'Set a timer for ',
    reset_chat: 'Reset the chat',
    browser_navigate: 'Open the website ',
    browser_read_page: 'Read the current page',
    browser_click: 'Click ',
    spotify_now_playing: "What's playing on Spotify?",
    spotify_play_pause: 'Pause the music',
    spotify_next: 'Skip to the next track',
    spotify_previous: 'Go to the previous track',
    spotify_set_volume: 'Set the volume to ',
    spotify_play: 'Play the song ',
    spotify_play_playlist: 'Play my playlist ',
    spotify_queue: 'Queue up the song ',
    spotify_list_playlists: 'List my playlists',
    spotify_list_devices: 'List my Spotify devices',
    spotify_transfer_playback: 'Move playback to ',
  }

  // The palette is open whenever the input begins with "/" and there are matches.
  $: query = text.startsWith('/') ? text.slice(1).toLowerCase() : null
  $: matches =
    query !== null
      ? $tools.filter(
          (t) =>
            t.name.toLowerCase().includes(query) ||
            t.description.toLowerCase().includes(query),
        )
      : []
  $: showPalette = query !== null && matches.length > 0
  $: if (selected >= matches.length) selected = 0

  function choose(tool: Tool) {
    text = TEMPLATES[tool.name] ?? tool.description
    inputEl?.focus()
  }

  async function submit() {
    const t = text.trim()
    if (!t || t.startsWith('/')) return
    text = ''
    await sendMessage(t)
  }

  function onKey(e: KeyboardEvent) {
    if (showPalette) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        selected = (selected + 1) % matches.length
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        selected = (selected - 1 + matches.length) % matches.length
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        choose(matches[selected])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        text = ''
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
    <div class="palette panel">
      <div class="palette-hint">Tools · ↑↓ to navigate, ↵ to insert</div>
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
