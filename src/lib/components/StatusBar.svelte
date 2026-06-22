<script lang="ts">
  import { status, active, connected } from '../stores'
</script>

<div class="status">
  <div class="line">
    <span class="dot {$connected ? 'on' : 'off'}"></span>
    <span class="k">link</span>
    <span class="v">{$connected ? 'connected' : 'offline'}</span>
  </div>
  <div class="line">
    <span class="dot {$active ? 'on' : 'idle'}"></span>
    <span class="k">session</span>
    <span class="v">{$active ? 'active' : 'asleep'}</span>
  </div>
  <div class="line">
    <span class="k">state</span>
    <span class="v big">{$status}</span>
  </div>
</div>

<style>
  .status { display: flex; flex-direction: column; gap: 12px; }
  .line { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .k {
    color: var(--text-dim);
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    min-width: 58px;
  }
  .v { color: var(--text); }
  .v.big { font-size: 15px; color: var(--accent); letter-spacing: 0.08em; }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--text-dim); }
  .dot.on { background: var(--ok); box-shadow: 0 0 8px var(--ok); }
  .dot.idle { background: var(--warn); }
  .dot.off { background: #6b7280; }
</style>
