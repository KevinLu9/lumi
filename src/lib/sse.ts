import {
  status, active, ttsPlaying, transcript, toolCalls, nowPlaying, connected,
  type Status,
} from './stores'

type Event = Record<string, any> & { type: string }

function handle(ev: Event) {
  switch (ev.type) {
    case 'snapshot':
      status.set(ev.status as Status)
      active.set(!!ev.active)
      ttsPlaying.set(!!ev.tts_playing)
      transcript.set(ev.transcript ?? [])
      nowPlaying.set(ev.now_playing ?? null)
      break
    case 'status':
      status.set(ev.status as Status)
      break
    case 'active_state':
      active.set(!!ev.active)
      ttsPlaying.set(!!ev.tts_playing)
      break
    case 'user_transcript':
      transcript.update((t) => [...t, { role: 'user', text: ev.text }])
      break
    case 'lumi_message':
      transcript.update((t) => [...t, { role: 'lumi', text: ev.text }])
      break
    case 'tool_call':
      toolCalls.update((t) =>
        [{ name: ev.name, args: ev.args ?? {}, result: ev.result ?? '', ts: Date.now() }, ...t].slice(0, 50),
      )
      break
    case 'chat_reset':
      transcript.set([{ role: 'system', text: 'Chat reset' }])
      break
    case 'now_playing':
      nowPlaying.set(ev.track ?? null)
      break
    // 'lumi_sentence' and 'timer' are intentionally ignored here.
  }
}

export function connectSSE(): EventSource {
  const es = new EventSource('/api/stream')
  es.onopen = () => connected.set(true)
  es.onerror = () => connected.set(false)
  es.onmessage = (e) => {
    try {
      handle(JSON.parse(e.data))
    } catch {
      /* ignore malformed frames / pings */
    }
  }
  return es
}
