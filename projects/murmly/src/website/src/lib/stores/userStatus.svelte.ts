import { browser } from "$app/environment";
import { authStore } from "./auth.svelte";
import { errorStore } from "./error.svelte";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const PING_INTERVAL = 30000; // 30 seconds

interface UserStatus {
  id: number;
  username: string;
  is_online: boolean;
  last_seen: string | null;
  has_chat: boolean;
  last_message?: {
    content: string;
    timestamp: string;
    is_mine: boolean;
  } | null;
}

function createUserStatusStore() {
  let state = $state<{
    users: UserStatus[];
    pingInterval: number | null;
  }>({
    users: [],
    pingInterval: null
  });

  async function fetchUsers() {
    if (!authStore.current.token) return;

    try {
      const response = await fetch(`${API_URL}/users/online`, {
        headers: { Authorization: `Bearer ${authStore.current.token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }

      state.users = await response.json();
    } catch (e: any) {
      errorStore.setError(`Failed to fetch users: ${e.message}`, "User Status Error");
    }
  }

  async function pingServer() {
    if (!authStore.current.token) return;

    try {
      const response = await fetch(`${API_URL}/users/ping`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authStore.current.token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to ping server');
      }
    } catch (e: any) {
      console.error('Failed to ping server:', e);
    }
  }

  function startPingInterval() {
    if (browser && !state.pingInterval) {
      state.pingInterval = window.setInterval(pingServer, PING_INTERVAL);
    }
  }

  function stopPingInterval() {
    if (browser && state.pingInterval) {
      clearInterval(state.pingInterval);
      state.pingInterval = null;
    }
  }

  return {
    get users() { return state.users; },
    fetchUsers,
    startPingInterval,
    stopPingInterval
  };
}

export const userStatusStore = createUserStatusStore(); 