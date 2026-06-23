<script lang="ts">
  import {
    Sun,
    CloudSun,
    Cloud,
    CloudFog,
    CloudDrizzle,
    CloudRain,
    CloudSnow,
    CloudLightning,
    Droplets,
  } from "@lucide/svelte";
  import type { Component } from "svelte";
  import type { ForecastDay } from "../stores";

  export let location: string;
  export let days: ForecastDay[];

  // Map a WWO weather code (from wttr.in) to a Lucide icon.
  function iconFor(code: number): Component {
    if (code === 113) return Sun;
    if (code === 116) return CloudSun;
    if (code === 119 || code === 122) return Cloud;
    if ([143, 248, 260].includes(code)) return CloudFog;
    if ([200, 386, 389, 392, 395].includes(code)) return CloudLightning;
    // Snow / sleet / freezing.
    if (
      [
        179, 182, 185, 227, 230, 281, 284, 311, 314, 317, 320, 323, 326, 329,
        332, 335, 338, 350, 362, 365, 368, 371, 374, 377,
      ].includes(code)
    )
      return CloudSnow;
    // Heavier rain / showers.
    if ([299, 302, 305, 308, 356, 359].includes(code)) return CloudRain;
    // Light / patchy rain & drizzle.
    if ([176, 263, 266, 293, 296, 353].includes(code)) return CloudDrizzle;
    return Cloud;
  }
</script>

<div class="widget">
  <div class="loc">{location}</div>
  <div class="days">
    {#each days as d}
      {@const Icon = iconFor(d.code)}
      <div class="day" title={d.desc}>
        <div class="dow">{d.day}</div>
        <Icon size={26} strokeWidth={1.6} />
        <div class="temps">
          <span class="max">{d.max}°</span><span class="min">{d.min}°</span>
        </div>
        <div class="rain" class:dry={d.rain === 0}>
          <Droplets size={10} strokeWidth={2} />{d.rain}%
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .widget {
    align-self: flex-start;
    max-width: 85%;
    border: 1px solid var(--panel-border);
    border-radius: 14px;
    background: rgba(245, 158, 11, 0.06);
    padding: 10px 12px;
  }
  .loc {
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 8px;
  }
  .days {
    display: flex;
    gap: 8px;
  }
  .day {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    flex: 1;
    min-width: 64px;
    padding: 8px 6px;
    border-radius: 10px;
    background: rgba(0, 0, 0, 0.18);
    color: var(--accent);
  }
  .dow {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text);
  }
  .temps {
    display: flex;
    gap: 5px;
    align-items: baseline;
    font-size: 13px;
  }
  .temps .max {
    color: var(--text);
    font-weight: 600;
  }
  .temps .min {
    color: var(--text-dim);
  }
  .rain {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-size: 10px;
    color: #7dd3fc;
  }
  .rain.dry {
    color: var(--text-dim);
    opacity: 0.6;
  }
</style>
