import { getOnlineUsers } from "$lib/apis"; // Your API function
import { authStore } from "$lib/stores/auth.svelte";

interface ChatState {
  onlineUsers: User[];
  messagesByPeer: Map<number, Message[]>;
  activeChatUser: User | null;
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

    setActiveChatUser(user: User | null) {
      state.activeChatUser = user;
      if (user) {
        state.newChats.delete(user.id.toString());
        if (!state.messagesByPeer.has(user.id)) {
          state.messagesByPeer = new Map(
            state.messagesByPeer.set(user.id, []),
          );
        }
      }
    },

    addMessage(message: Message) {
      const peer = message.isMine ? message.recipient.id : message.sender.id;
      const userMessages = state.messagesByPeer.get(peer) || [];
      // Ensure a new Map instance is created for reactivity
      const newPeerMessages = [...userMessages, message];
      state.messagesByPeer = new Map(
        state.messagesByPeer.set(peer, newPeerMessages),
      );
    },

    async fetchOnlineUsers(token: string) {
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
    },

    updateMessageDeliveryStatus(
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
          console.log(
            `Delivery status updated for ${recipientId} at ${clientTimestamp}: ${delivered}`,
          );
        } else {
          console.warn(
            `Could not find message for delivery status update: ${recipientId}, ${clientTimestamp}`,
          );
        }
      }
    },

    reset() {
      state.onlineUsers = [];
      state.messagesByPeer = new Map();
      state.activeChatUser = null;
      state.isFetchingOnlineUsers = false;
      state.newChats = new Set();
      console.log("Chat store reset.");
    },
  };
}

export const chatStore = createChatStore();
