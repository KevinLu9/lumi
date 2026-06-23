<script lang="ts">
  import StatusBar from "./StatusBar.svelte";
  import ControlButtons from "./ControlButtons.svelte";
</script>

<aside class="left">
  <div class="panel block">
    <h2 class="panel-title">System</h2>
    <StatusBar />
  </div>
  <div class="panel block">
    <h2 class="panel-title">Controls</h2>
    <ControlButtons />
  </div>
</aside>

<style>
  .left {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 18px;
    overflow-y: auto;
  }
  .block {
    padding: 16px;
  }
</style>
