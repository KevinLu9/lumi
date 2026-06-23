<script lang="ts">
  import { activate, deactivate, interrupt, reset } from "../api";
  import { active } from "../stores";
</script>

<div class="controls">
  {#if $active}
    <button class="btn" on:click={deactivate}>Sleep</button>
  {:else}
    <button class="btn active" on:click={activate}>Wake</button>
  {/if}
  <button class="btn danger" on:click={interrupt}>Interrupt</button>
  <button class="btn" on:click={reset}>Reset chat</button>
</div>

<style>
  .controls {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
</style>
