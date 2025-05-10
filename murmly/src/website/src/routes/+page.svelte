<script lang="ts">
  import Login from "$lib/components/Login.svelte";
  import Chat from "$lib/components/Chat.svelte";
  import { errorStore } from "$lib/stores/error.svelte";
  import { authStore } from "$lib/stores/auth.svelte";
  import { alertStore } from "$lib/stores/alert.svelte";
  import { fade, fly } from "svelte/transition";

  $inspect(errorStore.current);
</script>

{#if errorStore.hasError()}
  <div
    class="flex absolute top-1 z-100 flex-col items-center justify-center w-screen"
  >
    <div class="flex justify-center alert alert-error w-fit m-4 shadow-2xl">
      <div class="flex-1 text-2xl">
        <h1>{errorStore.current?.code}</h1>
        <h1>{errorStore.current?.message}</h1>
      </div>
      <button class="btn" onclick={() => errorStore.clearError()}>Close</button>
    </div>
  </div>
{/if}

{#if !authStore.current.isAuthenticated}
  <Login />
{:else}
  <Chat />
{/if}

{#if alertStore.current && alertStore.hasAlert()}
  <div
    in:fly={{ y: 100, duration: 300 }}
    out:fly={{ y: 100, duration: 300 }}
    class="flex absolute bottom-10 right-10 z-100 w-fit"
  >
    <div
      class="flex justify-center alert alert-{alertStore.current
        ?.type} w-fit m-4 shadow-2xl"
    >
      <div class="flex-1 text-xl">{alertStore.current.message}</div>
    </div>
  </div>
{/if}
