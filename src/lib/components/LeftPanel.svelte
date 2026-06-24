<script lang="ts">
  import StatusBar from "./StatusBar.svelte";
  import ControlButtons from "./ControlButtons.svelte";
  import ModelPicker from "./ModelPicker.svelte";
  import Schedules from "./Schedules.svelte";
</script>

<aside class="left">
  <div class="panel block">
    <h2 class="panel-title">System</h2>
    <StatusBar />
  </div>
  <div class="panel block">
    <h2 class="panel-title">Controls</h2>
    <ControlButtons />
    <div class="model"><ModelPicker /></div>
  </div>
  <div class="panel block sched">
    <Schedules />
  </div>
</aside>

<style>
  .left {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 18px;
    /* The aside itself fills the column and never scrolls; the Schedules list
       below absorbs the leftover height and scrolls on its own. */
    min-height: 0;
    overflow: hidden;
  }
  .block {
    padding: 16px;
  }
  .model {
    margin-top: 12px;
  }
  /* Let the schedules panel take the remaining vertical space. */
  .sched {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
</style>
