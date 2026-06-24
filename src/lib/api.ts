async function post(path: string, body?: unknown): Promise<void> {
  await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export const sendMessage = (text: string) => post("/api/message", { text });
export const interrupt = () => post("/api/interrupt");
export const reset = () => post("/api/reset");
export const activate = () => post("/api/activate");
export const deactivate = () => post("/api/deactivate");

import type { ToolModule, NowPlaying, Schedule, Model } from "./stores";

export async function fetchModels() {
  const r = await fetch("/api/model");
  return r.json() as Promise<{
    current: { provider: string; model: string };
    models: Model[];
  }>;
}

export async function setModel(provider: string, model: string) {
  const r = await fetch("/api/model", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, model }),
  });
  return r.json() as Promise<{
    ok: boolean;
    error?: string;
    current?: { provider: string; model: string };
  }>;
}

export async function fetchTools() {
  const r = await fetch("/api/tools");
  return r.json() as Promise<{ modules: ToolModule[]; active: string[] }>;
}

export async function fetchNowPlaying() {
  const r = await fetch("/api/spotify/now-playing");
  return r.json() as Promise<{ configured: boolean } & NowPlaying>;
}

export const spotifyControl = (action: "play_pause" | "next" | "previous") =>
  post("/api/spotify/control", { action });

export async function fetchSchedules() {
  const r = await fetch("/api/schedules");
  return r.json() as Promise<{ schedules: Schedule[] }>;
}

export async function createSchedule(when: string, prompt: string, label = "") {
  const r = await fetch("/api/schedules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ when, prompt, label }),
  });
  return r.json() as Promise<{ ok: boolean; error?: string; id?: string }>;
}

export async function updateSchedule(
  id: string,
  fields: { when?: string; prompt?: string; label?: string },
) {
  const r = await fetch(`/api/schedules/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  return r.json() as Promise<{ ok: boolean; error?: string }>;
}

export const toggleSchedule = (id: string, enabled: boolean) =>
  post(`/api/schedules/${id}/toggle`, { enabled });

export const deleteSchedule = (id: string) =>
  fetch(`/api/schedules/${id}`, { method: "DELETE" });
