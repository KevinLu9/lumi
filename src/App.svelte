<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { connectSSE } from "./lib/sse";
  import { AudioBridge } from "./lib/audio/bridge";
  import { status, micOn } from "./lib/stores";
  import Orb from "./lib/components/Orb.svelte";
  import Particles from "./lib/components/Particles.svelte";
  import Transcript from "./lib/components/Transcript.svelte";
  import ChatInput from "./lib/components/ChatInput.svelte";
  import LeftPanel from "./lib/components/LeftPanel.svelte";
  import RightPanel from "./lib/components/RightPanel.svelte";

  let es: EventSource;
  let bridge: AudioBridge;

  async function toggleMic() {
    if (!bridge) return;
    if ($micOn) {
      bridge.stopMic();
      micOn.set(false);
      return;
    }
    if (!window.isSecureContext || !navigator.mediaDevices) {
      alert(
        "The microphone is blocked because this page is not a secure context.\n\n" +
          "Browsers only allow mic access over https or on localhost. " +
          "To use voice from another device, serve Lumi over https (see README), " +
          "or just type in the box below — that works anywhere.",
      );
      return;
    }
    try {
      await bridge.startMic();
      micOn.set(true);
    } catch (e) {
      console.error("mic error", e);
      alert("Could not access the microphone. Check browser permissions.");
    }
  }

  onMount(() => {
    es = connectSSE();
    bridge = new AudioBridge();
  });

  onDestroy(() => {
    es?.close();
    bridge?.stopMic();
  });
</script>

<Particles />

<div class="app">
  <LeftPanel />

  <main class="center">
    <header class="brand">
      <span class="logo">◈</span> LUMI
    </header>
    <div class="stage">
      <Orb status={$status} />
    </div>
    <Transcript />
    <ChatInput onToggleMic={toggleMic} />
  </main>

  <RightPanel />
</div>

<style>
  .app {
    display: grid;
    grid-template-columns: 300px 1fr 340px;
    height: 100%;
    position: relative;
    z-index: 1;
  }
  .center {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 22px;
    padding: 24px;
    overflow: hidden;
  }
  .brand {
    font-size: 18px;
    letter-spacing: 0.5em;
    font-weight: 600;
    color: var(--text);
    align-self: flex-start;
  }
  .logo {
    color: var(--accent);
    margin-right: 6px;
  }
  .stage {
    flex: 1;
    display: grid;
    place-items: center;
    min-height: 0;
  }

  /* Tablet / mobile: stack into a single scrollable column with the orb +
     transcript + input first, then controls, then the info panels. */
  @media (max-width: 1100px) {
    .app {
      display: flex;
      flex-direction: column;
      height: auto;
      min-height: 100%;
    }
    .center {
      order: -1;
      overflow: visible;
      padding: 16px;
      gap: 18px;
    }
    .stage {
      flex: none;
      padding: 8px 0;
    }
  }

  @media (max-width: 700px) {
    .brand {
      font-size: 15px;
      letter-spacing: 0.35em;
      align-self: center;
    }
    .center {
      padding: 14px;
    }
  }
</style>
