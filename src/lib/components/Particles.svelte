<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { status } from "../stores";

  let container: import("@tsparticles/engine").Container | undefined;
  let destroyed = false;

  // Particles speed up subtly while Lumi is thinking/speaking. New particles adopt
  // the speed as they respawn at the edges.
  $: if (container) {
    const busy = $status === "thinking" || $status === "speaking";
    (container as any).options.particles.move.speed = busy ? 1.6 : 0.5;
  }

  onMount(async () => {
    const { tsParticles } = await import("@tsparticles/engine");
    const { loadSlim } = await import("@tsparticles/slim");
    await loadSlim(tsParticles);
    if (destroyed) return;

    container = await tsParticles.load({
      id: "tsparticles",
      options: {
        fullScreen: { enable: true, zIndex: 0 },
        background: { color: "transparent" },
        fpsLimit: 60,
        detectRetina: true,
        particles: {
          number: { value: 180, density: { enable: true } },
          color: { value: ["#fb923c", "#f59e0b", "#ffb86b"] },
          links: {
            enable: true,
            distance: 140,
            color: "#fb923c",
            opacity: 0.18,
            width: 1,
          },
          move: {
            enable: true,
            speed: 0.5,
            direction: "none",
            outModes: { default: "out" },
          },
          opacity: {
            value: { min: 0.15, max: 0.5 },
            animation: { enable: true, speed: 0.5, sync: false },
          },
          size: { value: { min: 1, max: 3 } },
        },
        interactivity: {
          events: {
            onHover: { enable: true, mode: "grab" },
            resize: { enable: true },
          },
          modes: {
            grab: { distance: 160, links: { opacity: 0.35 } },
          },
        },
      },
    });
  });

  onDestroy(() => {
    destroyed = true;
    container?.destroy();
  });
</script>
