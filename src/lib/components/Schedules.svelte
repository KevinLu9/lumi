<script lang="ts">
  import { onMount } from "svelte";
  import { Clock, Plus, Pencil, Trash2, Power } from "@lucide/svelte";
  import { schedules, type Schedule } from "../stores";
  import {
    fetchSchedules,
    createSchedule,
    updateSchedule,
    toggleSchedule,
    deleteSchedule,
  } from "../api";

  let when = "";
  let prompt = "";
  let label = "";
  let error = "";
  let adding = false;
  let open = false;
  let editingId: string | null = null; // null = creating a new schedule
  let expanded = new Set<string>(); // ids of cards showing their full prompt

  function toggleExpand(id: string) {
    if (expanded.has(id)) expanded.delete(id);
    else expanded.add(id);
    expanded = expanded; // reassign so Svelte re-renders
  }

  // Click-to-fill examples covering the friendly and cron forms the backend accepts.
  const whenExamples = [
    { value: "07:30", hint: "Every day at 7:30am" },
    { value: "6pm weekdays", hint: "Mon to Fri at 6:00pm" },
    { value: "09:15 on mon,wed,fri", hint: "Mon, Wed & Fri at 9:15am" },
    { value: "*/30 * * * *", hint: "Cron: every 30 minutes" },
    { value: "0 8 * * 0", hint: "Cron: Sundays at 8:00am" },
  ];

  onMount(async () => {
    try {
      const { schedules: s } = await fetchSchedules();
      schedules.set(s);
    } catch {
      /* backend may still be loading */
    }
  });

  function resetForm() {
    when = prompt = label = "";
    error = "";
    open = false;
    editingId = null;
  }

  function startCreate() {
    if (open && editingId === null) {
      resetForm();
      return;
    }
    when = prompt = label = "";
    error = "";
    editingId = null;
    open = true;
  }

  function startEdit(j: Schedule) {
    editingId = j.id;
    when = j.cron; // the cron is the source of truth and always re-parses cleanly
    prompt = j.prompt;
    label = j.label;
    error = "";
    open = true;
  }

  async function submit() {
    error = "";
    if (!when.trim() || !prompt.trim()) {
      error = "Time and prompt are required.";
      return;
    }
    adding = true;
    try {
      const r = editingId
        ? await updateSchedule(editingId, {
            when: when.trim(),
            prompt: prompt.trim(),
            label: label.trim(),
          })
        : await createSchedule(when.trim(), prompt.trim(), label.trim());
      if (!r.ok) {
        error = r.error || "Could not save schedule.";
        return;
      }
      resetForm();
      const { schedules: s } = await fetchSchedules();
      schedules.set(s);
    } catch {
      error = "Request failed.";
    } finally {
      adding = false;
    }
  }

  async function toggle(id: string, enabled: boolean) {
    await toggleSchedule(id, enabled);
    const { schedules: s } = await fetchSchedules();
    schedules.set(s);
  }

  async function remove(id: string) {
    await deleteSchedule(id);
    if (editingId === id) resetForm();
    const { schedules: s } = await fetchSchedules();
    schedules.set(s);
  }

  function nextLabel(next: number | null): string {
    if (!next) return "";
    const d = new Date(next * 1000);
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const time = d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    if (sameDay) return `next today ${time}`;
    const day = d.toLocaleDateString([], { weekday: "short" });
    return `next ${day} ${time}`;
  }
</script>

<div class="head">
  <h2 class="panel-title">Schedules</h2>
  <button class="addbtn" title="Add schedule" on:click={startCreate}>
    <Plus size={14} strokeWidth={2.4} />
  </button>
</div>

{#if open}
  <form class="form" on:submit|preventDefault={submit}>
    {#if editingId}<div class="form-title">Edit schedule</div>{/if}
    <input
      class="fld"
      bind:value={when}
      placeholder="When: a time or a cron expression"
    />
    <div class="examples">
      <span class="ex-label">Try:</span>
      {#each whenExamples as ex}
        <button
          type="button"
          class="ex"
          title={ex.hint}
          on:click={() => (when = ex.value)}
        >
          {ex.value}
        </button>
      {/each}
    </div>
    <textarea
      class="fld prompt"
      bind:value={prompt}
      rows="3"
      placeholder="Prompt: e.g. Give me today's weather"></textarea>
    <input class="fld" bind:value={label} placeholder="Label (optional)" />
    {#if error}<div class="err">{error}</div>{/if}
    <div class="actions">
      <button type="button" class="ghost" on:click={resetForm}>Cancel</button>
      <button type="submit" class="primary" disabled={adding}>
        {adding ? "Saving…" : editingId ? "Save" : "Add"}
      </button>
    </div>
  </form>
{/if}

<div class="list">
  {#each $schedules as j (j.id)}
    <div class="job" class:off={!j.enabled} class:editing={editingId === j.id}>
      <button class="summary" on:click={() => toggleExpand(j.id)}>
        <span class="chev" class:open={expanded.has(j.id)}>▸</span>
        <div class="info">
          <div class="name">{j.label || j.prompt}</div>
          <div class="meta">
            <Clock size={11} strokeWidth={2} />
            <span>{j.when}</span>
          </div>
        </div>
      </button>
      <div class="body">
        {#if j.enabled && j.next_run}
          <div class="nextline">{nextLabel(j.next_run)}</div>
        {/if}
        <div class="ctrls">
          <button
            class="ico"
            class:on={j.enabled}
            title={j.enabled ? "Disable" : "Enable"}
            on:click={() => toggle(j.id, !j.enabled)}
          >
            <Power size={14} strokeWidth={2} />
          </button>
          <button class="ico" title="Edit" on:click={() => startEdit(j)}>
            <Pencil size={14} strokeWidth={2} />
          </button>
          <button class="ico del" title="Delete" on:click={() => remove(j.id)}>
            <Trash2 size={14} strokeWidth={2} />
          </button>
        </div>
        {#if expanded.has(j.id)}
          <div class="full">{j.prompt}</div>
        {/if}
      </div>
    </div>
  {/each}
  {#if $schedules.length === 0}
    <div class="empty">
      No schedules. Add one, or ask Lumi to set a reminder.
    </div>
  {/if}
</div>

<style>
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .addbtn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    border: 1px solid var(--panel-border);
    background: transparent;
    color: var(--accent);
    cursor: pointer;
  }
  .addbtn:hover {
    background: rgba(245, 158, 11, 0.12);
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 10px 0;
  }
  .form-title {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
  }
  .fld {
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    padding: 7px 9px;
    color: var(--text);
    font-size: 12px;
    outline: none;
  }
  .fld:focus {
    border-color: var(--accent);
  }
  .prompt {
    resize: vertical;
    min-height: 56px;
    line-height: 1.45;
    font-family: inherit;
  }
  .examples {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 5px;
    margin: -1px 0 1px;
  }
  .ex-label {
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
  }
  .ex {
    font-size: 11px;
    font-family: ui-monospace, monospace;
    color: var(--accent);
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid var(--panel-border);
    border-radius: 6px;
    padding: 2px 6px;
    cursor: pointer;
  }
  .ex:hover {
    background: rgba(245, 158, 11, 0.16);
    border-color: var(--accent);
  }
  .err {
    color: #f87171;
    font-size: 11px;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .ghost,
  .primary {
    font-size: 12px;
    border-radius: 7px;
    padding: 6px 12px;
    cursor: pointer;
    border: 1px solid var(--panel-border);
  }
  .ghost {
    background: transparent;
    color: var(--text-dim);
  }
  .primary {
    background: var(--accent);
    border-color: var(--accent);
    color: #0a0a0a;
    font-weight: 600;
  }
  .primary:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 10px;
    /* Fill the leftover height of the panel and scroll internally, so the left
       aside never has to scroll. Falls back to a sensible cap if the panel
       isn't a flex parent (e.g. the stacked mobile layout). */
    flex: 1;
    min-height: 0;
    max-height: 320px;
    overflow-y: auto;
    /* room so cards don't sit flush against the scrollbar */
    padding-right: 2px;
  }
  .job {
    border: 1px solid var(--panel-border);
    border-radius: 10px;
    background: rgba(245, 158, 11, 0.05);
    overflow: hidden;
  }
  .job.off {
    opacity: 0.5;
  }
  .job.editing {
    border-color: var(--accent);
    background: rgba(245, 158, 11, 0.1);
  }
  .summary {
    display: flex;
    align-items: center;
    gap: 7px;
    width: 100%;
    padding: 8px 10px 4px;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
  }
  .chev {
    color: var(--accent);
    font-size: 10px;
    flex: none;
    transition: transform 0.15s ease;
  }
  .chev.open {
    transform: rotate(90deg);
  }
  .body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 10px 8px 26px;
  }
  .full {
    font-size: 12px;
    line-height: 1.5;
    color: var(--text-dim);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .nextline {
    font-size: 11px;
    color: var(--text-dim);
    font-family: ui-monospace, monospace;
  }
  .info {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .name {
    font-size: 13px;
    color: var(--text);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: var(--accent);
    font-family: ui-monospace, monospace;
  }
  .ctrls {
    display: flex;
    justify-content: flex-end;
    gap: 4px;
  }
  .ico {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
  }
  .ico:hover {
    background: rgba(255, 255, 255, 0.06);
    color: var(--text);
  }
  .ico.on {
    color: #4ade80;
  }
  .ico.del:hover {
    color: #f87171;
  }
  .empty {
    color: var(--text-dim);
    font-size: 12px;
  }
</style>
