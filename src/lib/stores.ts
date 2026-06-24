import { writable } from "svelte/store";

export type Status =
  | "idle"
  | "listening"
  | "recording"
  | "transcribing"
  | "thinking"
  | "speaking";

export type Usage = {
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
  reasoning: number;
};
export type ForecastDay = {
  date: string; // ISO yyyy-mm-dd
  day: string; // short weekday, e.g. "Tue"
  min: number;
  max: number;
  desc: string;
  code: number; // WWO condition code
  rain: number; // chance of rain %
};
export type TranscriptItem =
  | { role: "user" | "lumi" | "system"; text: string; usage?: Usage }
  | {
      role: "tool";
      name: string;
      args: Record<string, unknown>;
      result: string;
    }
  | { role: "weather"; location: string; days: ForecastDay[] }
  | { role: "error"; text: string; retry: string };
export type Tool = { name: string; description: string };
export type ToolModule = {
  name: string;
  description: string;
  default: boolean;
  tools: Tool[];
};

export const status = writable<Status>("idle");
export const active = writable(false);
export const ttsPlaying = writable(false);
export const transcript = writable<TranscriptItem[]>([]);
export const tools = writable<Tool[]>([]); // flat list (command palette)
export const toolModules = writable<ToolModule[]>([]); // grouped by tool file, for the Tools panel
export const activeTools = writable<Set<string>>(new Set()); // tools currently loaded into context
export type NowPlaying = {
  track: string | null;
  artist?: string;
  album?: string;
  image?: string | null;
  is_playing?: boolean;
  progress_ms?: number;
  duration_ms?: number;
};
export const nowPlaying = writable<NowPlaying | null>(null);
export type Schedule = {
  id: string;
  prompt: string;
  label: string;
  cron: string;
  when: string; // human-readable, e.g. "07:30 weekdays"
  enabled: boolean;
  next_run: number | null; // unix seconds
};
export const schedules = writable<Schedule[]>([]);

export type Model = { provider: string; model: string; label?: string };
export const models = writable<Model[]>([]); // curated catalog from the backend
export const currentModel = writable<{
  provider: string;
  model: string;
} | null>(null);

const zeroUsage = (): Usage => ({
  input: 0,
  output: 0,
  cache_read: 0,
  cache_write: 0,
  reasoning: 0,
});
// Today's cumulative token usage (persisted per-day on the backend).
export const usageToday = writable<Usage>(zeroUsage());
export const spotifyConfigured = writable(true);
export const connected = writable(false);
export const micOn = writable(false);
// Smoothed audio amplitude (0..1) of whichever stream is live: your mic while
// recording, Lumi's TTS while speaking. Drives the orb's reactive pulse/glow.
export const audioLevel = writable(0);
