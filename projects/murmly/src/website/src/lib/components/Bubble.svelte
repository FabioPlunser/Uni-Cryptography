<script lang="ts">
  let { msg } = $props();
  import { fly } from "svelte/transition";
</script>

{#if msg.isMine}
  <div
    in:fly|global={{ x: 200, duration: 300 }}
    out:fly|global={{ x: -200, duration: 300 }}
    class="chat chat-end"
  >
    <div class="chat-bubble chat-bubble-primary">
      {@html msg.content.replace(/\n/g, "<br>")}
    </div>
    <div class="chat-footer opacity-50 text-xs mt-1">
      {new Date(msg.timestamp).toLocaleTimeString()}
    </div>
  </div>
{:else}
  <div
    in:fly|global={{ x: -200, duration: 300 }}
    out:fly|global={{ x: 200, duration: 300 }}
    class="chat chat-start"
  >
    <div class="chat-bubble chat-bubble-secondary">
      {@html msg.content.replace(/\n/g, "<br>")}
    </div>
    <div class="chat-footer opacity-50 text-xs mt-1">
      {new Date(msg.timestamp).toLocaleTimeString()}
    </div>
  </div>
{/if}
