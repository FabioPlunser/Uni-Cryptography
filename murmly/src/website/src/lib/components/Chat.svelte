<!-- src/lib/components/Chat.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { cryptoStore } from "$lib/stores/crypto.svelte";
  import { chatStore } from "$lib/stores/chat.svelte";
  import { authStore } from "$lib/stores/auth.svelte";
  import { websocketStore } from "$lib/stores/websocket.svelte";
  import { fade, fly } from "svelte/transition";
  import Bubble from "$lib/components/Bubble.svelte";
  let messageInput = $state("");
  let messageContainerElement = $state<HTMLDivElement | null>(null);

  // Use derived state from chatStore for active user and their messages
  let activeChatUser = $derived(chatStore.current.activeChatUser);
  let messagesForActiveUser = $derived(chatStore.activeChatMessages);
  let onlineUsers = $derived(chatStore.current.onlineUsers);
  let currentUser = $derived(authStore.current.username);
  let newChats = $derived(chatStore.current.newChats);

  onMount(() => {
    if (authStore.current.token) {
      cryptoStore.initializeCryptography(authStore.current.token);
    }

    if (websocketStore.isConnected && authStore.current.token) {
      chatStore.fetchOnlineUsers(authStore.current.token);
    } else {
      chatStore.setActiveChatUser(null);
      websocketStore.connect();
    }
    const intervalId = setInterval(() => {
      if (authStore.current.token) {
        chatStore.fetchOnlineUsers(authStore.current.token);
      }
    }, 3000);

    return () => {
      clearInterval(intervalId);
    };
  });

  async function handleSendMessage(event: Event) {
    event.preventDefault();
    if (!activeChatUser || !messageInput.trim()) {
      alert("Please select a recipient and type a message.");
      return;
    }

    const success = await websocketStore.sendMessage(
      activeChatUser,
      authStore.current,
      messageInput,
    );
    if (success) {
      messageInput = "";
    }
  }

  function handleLogout() {
    authStore.logout();
  }

  async function selectUser(selectedUser: onlineUser) {
    chatStore.setActiveChatUser(selectedUser);
    // await chatStore.fetchChatHistory(authStore.current.token, selectedUser);
  }

  // Auto-scroll to bottom of messages
  $effect(() => {
    if (messagesForActiveUser && messageContainerElement) {
      // Timeout to allow DOM to update before scrolling
      setTimeout(() => {
        if (messageContainerElement) {
          messageContainerElement.scrollTop =
            messageContainerElement.scrollHeight;
        }
      }, 50);
    }
  });
</script>

<div
  class="flex flex-col h-screen w-screen items-center justify-center p-4 bg-base-300"
>
  <div
    class="w-full h-full max-w-5xl bg-base-100 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
  >
    <header class="navbar bg-base-200 p-4 border-b border-base-300">
      <div class="flex-1">
        <h1 class="font-bold text-xl text-primary">Murmly Chat</h1>
        {#if currentUser}
          <span class="text-sm text-neutral-content"
            >Logged in as: <span class="font-semibold">{currentUser}</span
            ></span
          >
        {/if}
      </div>
      <div class="flex-none">
        <button class="btn btn-outline btn-error btn-sm" onclick={handleLogout}>
          Logout
        </button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <aside
        class="w-1/3 md:w-1/4 bg-base-200 p-4 border-r border-base-300 overflow-y-auto"
      >
        <h2 class="text-lg font-semibold mb-3 text-neutral-content">
          Online Users
        </h2>
        {#if onlineUsers.length > 0}
          <ul class="menu gap-2 p-0 w-full">
            {#each onlineUsers as user (user)}
              <li class="">
                <button
                  class="card rounded-sm bg-gray-800 shadow-xml justify-start w-full text-left text-base-content hover:bg-base-300 relative
                  {activeChatUser?.id === user.id
                    ? 'bg-primary text-primary-content'
                    : ''}"
                  onclick={() => selectUser(user)}
                >
                  {user.username}
                </button>
              </li>
            {/each}
          </ul>
        {:else}
          <p class="text-sm text-gray-400">No other users online.</p>
        {/if}
      </aside>

      <!-- Chat Area -->
      <main class="flex-1 flex flex-col p-4">
        {#if activeChatUser}
          <h2
            class="text-xl font-semibold mb-4 text-neutral-content border-b pb-2 border-base-300"
          >
            Chat with: <span class="text-accent">{activeChatUser.username}</span
            >
          </h2>
          <div
            bind:this={messageContainerElement}
            class="flex-1 overflow-y-auto mb-4 space-y-4 pr-2"
          >
            {#each messagesForActiveUser as msg (msg.id)}
              <Bubble {msg} />
            {:else}
              <div class="flex items-center justify-center h-full">
                <p class="text-neutral-content opacity-70">
                  No messages yet with {activeChatUser.username}.
                </p>
              </div>
            {/each}
          </div>

          <form
            class="flex gap-2 pt-2 border-base-300"
            onsubmit={handleSendMessage}
          >
            <textarea
              onkeydown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              bind:value={messageInput}
              placeholder="Type your message..."
              class="textarea textarea-bordered flex-1 resize-none"
              rows="2"
              disabled={!activeChatUser}
            ></textarea>
            <div class="flex items-center h-full">
              <button
                type="submit"
                class="btn btn-primary"
                disabled={!activeChatUser || !messageInput.trim()}>Send</button
              >
            </div>
          </form>
        {:else}
          <div class="flex items-center justify-center h-full">
            <p class="text-xl text-neutral-content opacity-60">
              Select a user to start chatting.
            </p>
          </div>
        {/if}
      </main>
    </div>
  </div>
</div>
