// src/lib/stores/websocket.svelte.ts
import { authStore } from "./auth.svelte";
import { chatStore } from "./chat.svelte";
import { cryptoStore } from "./crypto.svelte";
import { errorStore } from "./error.svelte";
import { alertStore } from "./alert.svelte";

const WS_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000")
  .replace(/^http/, 'ws');

function createWebSocketStore() {
  let socket = $state<WebSocket | null>(null);
  let reconnectAttempts = $state(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  function connect() {
    const token = authStore.current.token;
    if (!token) {
      errorStore.setError("Cannot connect WebSocket: No auth token.", 500);
      return;
    }
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      console.log("WebSocket already open or connecting.");
      return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/${token}`;
    console.log(`Connecting WebSocket to ${wsUrl}`);
    const newSocket = new WebSocket(wsUrl);

    newSocket.onopen = () => {
      console.log("WebSocket connection established.");
      socket = newSocket;
      reconnectAttempts = 0;
    };

    newSocket.onmessage = async (event: MessageEvent) => {
      try {
        const payload: WebSocketPayload = JSON.parse(event.data as string);
        console.log("WebSocket message received:", payload);

        if (!payload.sender || !payload.content) {
          console.warn("Invalid message payload:", payload);
          return;
        }

        // Ensure cryptography is initialized
        if (!cryptoStore.currentDhParams || !cryptoStore.currentUserPubKey) {
          console.log("Initializing cryptography before processing message...");
          const initialized = await cryptoStore.initializeCryptography(authStore.current.token!);
          if (!initialized) {
            console.error("Failed to initialize cryptography");
            return;
          }
        }

        // Initialize chat with sender if it's a new chat
        if (payload.is_new_chat) {
          console.log("New chat detected, establishing secure channel...");
          const channelReady = await cryptoStore.ensureSecureChannel(authStore.current.token!, payload.sender.id);
          if (!channelReady) {
            console.error("Failed to establish secure channel for new chat");
            return;
          }
          console.log("Secure channel established successfully");
        }

        // Try to decrypt the message
        console.log("Attempting to decrypt message...");
        const decryptedContent = await cryptoStore.decryptWSMessage(payload.sender.id, payload.content);
        if (decryptedContent === null || decryptedContent.startsWith("[Decryption Failed")) {
          console.warn("Decryption failed for message:", payload);
          console.log("Message content:", payload.content);
          console.log("Sender ID:", payload.sender.id);
          return;
        }
        console.log("Message decrypted successfully");

        // Add the message to the chat store
        const newMessage: Message = {
          id: `${payload.timestamp}-${payload.sender.id}-${Math.random().toString(36).substring(2, 7)}`,
          sender: payload.sender,
          recipient: {
            id: authStore.current.id!,
            username: authStore.current.username!,
            public_key_b64: '',
            is_online: true,
            isAuthenticated: true,
            token: authStore.current.token!
          },
          content: decryptedContent,
          timestamp: payload.timestamp,
          isMine: false,
          type: payload.is_new_chat ? 'incoming' : 'status',
        };
        chatStore.addMessage(newMessage);

        // Play notification sound for new messages
        if (payload.is_new_chat && payload.sender.id !== chatStore.current.activeChatUser?.id) {
          const audio = new Audio('/notification.mp3');
          alertStore.setAlert(`New message from ${payload.sender.username}`, "info");
          audio.play().catch(e => console.log('Could not play notification sound:', e));
        }
      } catch (e: any) {
        console.error("Error processing WebSocket message:", e, event.data);
        errorStore.setError(`WebSocket message processing error: ${e.message}`, "WebSocket Error");
      }
    };

    // newSocket.onerror = (event: Event) => {
    //   console.error("WebSocket error:", event);
    //   errorStore.setError("WebSocket connection error occurred.", "WebSocket Error");
    //   // Consider if retry logic should also be here or only onclose
    // };

    // newSocket.onclose = (event: CloseEvent) => {
    //   console.log(`WebSocket connection closed: Code ${event.code}, Reason: ${event.reason}`);
    //   socket = null;
    //   if (authStore.current.isAuthenticated && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
    //     reconnectAttempts++;
    //     console.log(`Attempting to reconnect WebSocket (attempt ${reconnectAttempts})...`);
    //     setTimeout(connect, RECONNECT_DELAY * reconnectAttempts);
    //   } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    //     errorStore.setError("WebSocket disconnected after multiple retries. Please check your connection or log in again.", "WebSocket Error");
    //   }
    // };
  }

  async function sendMessage(recipient: User, sender: User, plainTextContent: string) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      errorStore.setError("WebSocket not connected. Cannot send message.", "WebSocket Error");
      return false;
    }
    if (!authStore.current.token) {
      errorStore.setError("Not authenticated. Cannot send message.", "WebSocket Error");
      return false;
    }

    // 1. Ensure secure channel (this might be async)
    const channelReady = await cryptoStore.ensureSecureChannel(authStore.current.token, recipient.id);
    if (!channelReady) {
      errorStore.setError(`Could not establish secure channel with ${recipient.id}. Message not sent.`, "Encryption Error");
      return false;
    }

    // 2. Encrypt the message
    const encryptedContent = await cryptoStore.encryptWSMessage(recipient.id, plainTextContent);
    if (!encryptedContent) {
      errorStore.setError(`Failed to encrypt message for ${recipient.id}.`, "Encryption Error");
      return false;
    }

    const outgoingTimestamp = new Date().toISOString();
    const payload: WebSocketPayload = {
      recipient: recipient,
      content: encryptedContent,
      timestamp: outgoingTimestamp,
    };

    try {
      socket.send(JSON.stringify(payload));
      console.log("WebSocket message sent:", payload);

      // Optimistically add to chatStore (or let server confirm, then add)
      // For optimistic UI, we need a timestamp that will match server's delivery status
      // The server's current implementation uses `datetime.now().isoformat()` upon *sending* delivery status.
      // And `datetime.now().isoformat()` upon *receiving* a message to put in `message_json`.
      // This makes exact timestamp matching for delivery status tricky.
      // A robust solution would be for the client to generate a unique message ID, send it,
      // and the server includes this ID in the delivery status.
      // For now, we'll use the client's timestamp for the optimistic update.
      chatStore.addMessage({
        id: `${outgoingTimestamp}-${authStore.current.username}-${Math.random().toString(36).substring(2, 7)}`,
        sender: sender,
        recipient: recipient,
        content: plainTextContent, // Show plain text for outgoing
        timestamp: outgoingTimestamp,
        isMine: true,
        type: 'outgoing',
        delivered: undefined, // Awaiting confirmation
      });
      return true;
    } catch (e: any) {
      console.error("Error sending WebSocket message:", e);
      errorStore.setError(`Failed to send message: ${e.message}`, "WebSocket Error");
      return false;
    }
  }

  function disconnect() {
    if (socket) {
      console.log("Disconnecting WebSocket.");
      reconnectAttempts = MAX_RECONNECT_ATTEMPTS; // Prevent auto-reconnect on manual disconnect
      socket.close();
      socket = null;
    }
  }

  return {
    get current() { return socket; }, // Expose the raw socket if needed, or just status
    get isConnected() { return socket?.readyState === WebSocket.OPEN; },
    connect,
    disconnect,
    sendMessage,
  };
}

export const websocketStore = createWebSocketStore();
