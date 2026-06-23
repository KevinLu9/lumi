import { writable } from 'svelte/store'

export type Status =
  | 'idle' | 'listening' | 'recording' | 'transcribing' | 'thinking' | 'speaking'

export type Usage = {
  input: number
  output: number
  cache_read: number
  cache_write: number
  reasoning: number
}
export type ForecastDay = {
  date: string // ISO yyyy-mm-dd
  day: string // short weekday, e.g. "Tue"
  min: number
  max: number
  desc: string
  code: number // WWO condition code
  rain: number // chance of rain %
}
export type TranscriptItem =
  | { role: 'user' | 'lumi' | 'system'; text: string; usage?: Usage }
  | { role: 'tool'; name: string; args: Record<string, unknown>; result: string }
  | { role: 'weather'; location: string; days: ForecastDay[] }
export type Tool = { name: string; description: string }
export type ToolModule = { name: string; description: string; default: boolean; tools: Tool[] }

export const status = writable<Status>('idle')
export const active = writable(false)
export const ttsPlaying = writable(false)
export const transcript = writable<TranscriptItem[]>([])
export const tools = writable<Tool[]>([])           // flat list (command palette)
export const toolModules = writable<ToolModule[]>([])  // grouped by tool file, for the Tools panel
export const activeTools = writable<Set<string>>(new Set())  // tools currently loaded into context
export const nowPlaying = writable<string | null>(null)
export const spotifyConfigured = writable(true)
export const connected = writable(false)
export const micOn = writable(false)
