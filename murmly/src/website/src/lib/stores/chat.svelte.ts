import { getChatHistory, getOnlineUsers } from "$lib/apis"; // Your API function
import { authStore } from "./auth.svelte";
import { cryptoStore } from "./crypto.svelte";
import { errorStore } from "./error.svelte";

interface ChatState {
  onlineUsers: onlineUser[];
  messagesByPeer: Map<number, Message[]>;
  activeChatUser: onlineUser | null;
  isFetchingOnlineUsers: boolean;
  newChats: Set<string>;
}

function createChatStore() {
  let state = $state<ChatState>({
    onlineUsers: [],
    messagesByPeer: new Map(),
    activeChatUser: null,
    isFetchingOnlineUsers: false,
    newChats: new Set(),
  });

  async function fetchChatHistory(token: string, selected_user: onlineUser) {
    try {
      if (!cryptoStore.currentDhParams || !cryptoStore.currentUserPubKey) {
        const initialized = await cryptoStore.initializeCryptography(authStore.current.token!);
        if (!initialized) {
          console.error("Failed to initialize cryptography");
          return;
        }
      }
      const channelReady = await cryptoStore.ensureSecureChannel(token, selected_user.id);
      if (!channelReady) {
        errorStore.setError("Failed to establish secure channel", 401);
        throw new Error("Failed to establish secure channel");
      }
      const history = await getChatHistory(selected_user.id, token);
      const decriptedHistory = await Promise.all(
        history.map(async (message) => {
          const decryptedContent = await cryptoStore.decryptWSMessage(
            selected_user.id,
            message.content,
          );
          console.log("Decrypted content:", decryptedContent);
          if (decryptedContent === null || decryptedContent.startsWith("[Decryption Failed")) {
            console.error("Decryption failed for message:", message);
            return null;
          }
          return {
            ...message,
            content: decryptedContent
          };
        }),
      );
      state.messagesByPeer = new Map(
        state.messagesByPeer.set(selected_user.id, decriptedHistory.filter((message) => message !== null)),
      );
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
      errorStore.setError(`Failed to fetch chat history: ${error}`, 401);
    }
  }

  function updateMessageDeliveryStatus(
    recipientId: number,
    clientTimestamp: string,
    delivered: boolean,
  ) {
    const messages = state.messagesByPeer.get(recipientId);
    if (messages) {
      const msgIndex = messages.findIndex(
        (m) =>
          m.isMine &&
          m.recipient.id === recipientId &&
          m.timestamp === clientTimestamp,
      );

      if (msgIndex > -1) {
        const updatedMessages = [...messages];
        updatedMessages[msgIndex] = {
          ...updatedMessages[msgIndex],
          delivered: delivered,
          type: "outgoing",
        };
        // When updating messagesByPeer, ensure a new Map instance is created if you
        // want to trigger derived stores that depend on the Map reference itself.
        // However, activeChatMessages depends on the content of the array for a specific peer.
        // Sorting will return a new array reference, which is good.
        state.messagesByPeer = new Map(
          state.messagesByPeer.set(recipientId, updatedMessages), // No need to sort here, activeChatMessages will sort
        );
      } else {
        console.warn(
          `Could not find message for delivery status update: ${recipientId}, ${clientTimestamp}`,
        );
      }
    }
  }
  function setActiveChatUser(user: onlineUser | null) {
    state.activeChatUser = user;
    if (user) {
      state.newChats.delete(user.id.toString());
      if (!state.messagesByPeer.has(user.id)) {
        state.messagesByPeer = new Map(
          state.messagesByPeer.set(user.id, []),
        );
      }
    }
  }
  function addMessage(message: Message) {
    const peer = message.isMine ? message.recipient.id : message.sender.id;
    const userMessages = state.messagesByPeer.get(peer) || [];
    // Ensure a new Map instance is created for reactivity
    const newPeerMessages = [...userMessages, message];
    state.messagesByPeer = new Map(
      state.messagesByPeer.set(peer, newPeerMessages),
    );
  }

  async function fetchOnlineUsers(token: string) {
    if (!token) {
      console.warn("fetchOnlineUsers called without a token.");
      return;
    }
    state.isFetchingOnlineUsers = true;
    try {
      const users = await getOnlineUsers(token);
      state.onlineUsers = users;
    } catch (error) {
      console.error("Failed to fetch online users:", error);
      state.onlineUsers = [];
    } finally {
      state.isFetchingOnlineUsers = false;
    }
  }

  function reset() {
    state.onlineUsers = [];
    state.messagesByPeer = new Map();
    state.activeChatUser = null;
    state.isFetchingOnlineUsers = false;
    state.newChats = new Set();
  }

  return {
    get current() {
      return state;
    },

    get activeChatMessages() {
      if (!state.activeChatUser) return [];
      const messages = state.messagesByPeer.get(state.activeChatUser.id) || [];
      return messages;
    },

    get hasNewChats(): boolean {
      return state.newChats.size > 0;
    },

    fetchChatHistory,
    fetchOnlineUsers,
    setActiveChatUser,
    addMessage,
    reset,
  };
}

export const chatStore = createChatStore();
