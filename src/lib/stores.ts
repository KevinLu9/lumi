import { writable } from 'svelte/store'

export type Status =
  | 'idle' | 'listening' | 'recording' | 'transcribing' | 'thinking' | 'speaking'

export type TranscriptItem = { role: 'user' | 'lumi' | 'system'; text: string }
export type Tool = { name: string; description: string }
export type ToolCall = {
  name: string
  args: Record<string, unknown>
  result: string
  ts: number
}

export const status = writable<Status>('idle')
export const active = writable(false)
export const ttsPlaying = writable(false)
export const transcript = writable<TranscriptItem[]>([])
export const tools = writable<Tool[]>([])
export const toolCalls = writable<ToolCall[]>([])
export const nowPlaying = writable<string | null>(null)
export const spotifyConfigured = writable(true)
export const connected = writable(false)
export const micOn = writable(false)
