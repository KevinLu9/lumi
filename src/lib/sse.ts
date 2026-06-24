import {
  status,
  active,
  ttsPlaying,
  transcript,
  activeTools,
  nowPlaying,
  schedules,
  connected,
  currentModel,
  usageToday,
  type Status,
  type Usage,
} from "./stores";

type Event = Record<string, any> & { type: string };

const zeroUsage = (): Usage => ({
  input: 0,
  output: 0,
  cache_read: 0,
  cache_write: 0,
  reasoning: 0,
});

function handle(ev: Event) {
  switch (ev.type) {
    case "snapshot":
      status.set(ev.status as Status);
      active.set(!!ev.active);
      ttsPlaying.set(!!ev.tts_playing);
      transcript.set(ev.transcript ?? []);
      activeTools.set(new Set(ev.active_tools ?? []));
      nowPlaying.set(ev.now_playing ?? null);
      schedules.set(ev.schedules ?? []);
      currentModel.set(ev.model ?? null);
      usageToday.set(ev.usage_today ?? zeroUsage());
      break;
    case "status":
      status.set(ev.status as Status);
      break;
    case "active_state":
      active.set(!!ev.active);
      ttsPlaying.set(!!ev.tts_playing);
      break;
    case "user_transcript":
      transcript.update((t) => [...t, { role: "user", text: ev.text }]);
      break;
    case "lumi_message":
      transcript.update((t) => [
        ...t,
        { role: "lumi", text: ev.text, usage: ev.usage },
      ]);
      // Optimistic local bump; the next snapshot reconciles against the server's ledger.
      if (ev.usage)
        usageToday.update((u) => ({
          input: u.input + (ev.usage.input ?? 0),
          output: u.output + (ev.usage.output ?? 0),
          cache_read: u.cache_read + (ev.usage.cache_read ?? 0),
          cache_write: u.cache_write + (ev.usage.cache_write ?? 0),
          reasoning: u.reasoning + (ev.usage.reasoning ?? 0),
        }));
      break;
    case "tool_call":
      transcript.update((t) => [
        ...t,
        {
          role: "tool",
          name: ev.name,
          args: ev.args ?? {},
          result: ev.result ?? "",
        },
      ]);
      break;
    case "weather":
      transcript.update((t) => [
        ...t,
        { role: "weather", location: ev.location ?? "", days: ev.days ?? [] },
      ]);
      break;
    case "error":
      transcript.update((t) => [
        ...t,
        {
          role: "error",
          text: ev.message ?? "Something went wrong.",
          retry: ev.retry ?? "",
        },
      ]);
      break;
    case "chat_reset":
      transcript.set([{ role: "system", text: "Chat reset" }]);
      break;
    case "tools_active":
      activeTools.set(new Set(ev.names ?? []));
      break;
    case "model":
      currentModel.set({ provider: ev.provider, model: ev.model });
      // Usage is per-model: swap the displayed total to the newly selected model.
      if (ev.usage_today) usageToday.set(ev.usage_today);
      break;
    case "now_playing":
      nowPlaying.set(ev.track ?? null);
      break;
    case "schedules":
      schedules.set(ev.jobs ?? []);
      break;
    // 'lumi_sentence', 'timer' and 'schedule_fired' are intentionally ignored here.
  }
}

export function connectSSE(): EventSource {
  const es = new EventSource("/api/stream");
  es.onopen = () => connected.set(true);
  es.onerror = () => connected.set(false);
  es.onmessage = (e) => {
    try {
      handle(JSON.parse(e.data));
    } catch {
      /* ignore malformed frames / pings */
    }
  };
  return es;
}
