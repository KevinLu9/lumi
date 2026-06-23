async function post(path: string, body?: unknown): Promise<void> {
  await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

export const sendMessage = (text: string) => post('/api/message', { text })
export const interrupt = () => post('/api/interrupt')
export const reset = () => post('/api/reset')
export const activate = () => post('/api/activate')
export const deactivate = () => post('/api/deactivate')

import type { ToolModule } from './stores'

export async function fetchTools() {
  const r = await fetch('/api/tools')
  return r.json() as Promise<{ modules: ToolModule[]; active: string[] }>
}

export async function fetchNowPlaying() {
  const r = await fetch('/api/spotify/now-playing')
  return r.json() as Promise<{ configured: boolean; track: string | null }>
}
