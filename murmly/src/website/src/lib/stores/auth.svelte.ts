import { browser } from "$app/environment";
import { loginForToken, registerUser } from "$lib/apis";
import { cryptoStore } from "./crypto.svelte";
import { errorStore } from "./error.svelte";
import { chatStore } from "./chat.svelte";
import { websocketStore } from "./websocket.svelte";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface AuthState {
  token: string | null;
  username: string | null;
  isAuthenticated: boolean;
}

async function hashPassword(password: string): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(password));
  return btoa(String.fromCharCode(...new Uint8Array(hash)));
}

const initialAuthState: User = {
  id: 0,
  username: "",
  public_key_b64: "",
  is_online: false,
  isAuthenticated: false,
  token: "",
};



function createAuthStore() {
  let state = $state<User>(initialAuthState);

  if (browser) {
    const storedToken = localStorage.getItem("authToken");
    const storedUsername = localStorage.getItem("authUsername");
    if (storedToken && storedUsername) {
      state.token = storedToken;
      state.username = storedUsername;
      state.isAuthenticated = true;
    }
  }

  async function login(username: string, password: string): Promise<boolean> {
    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", await hashPassword(password));

      const response = await fetch(`${API_URL}/token`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Login failed");
      }

      const data = await response.json();
      state.token = data.access_token;
      state.username = username;
      state.isAuthenticated = true;

      console.log("Initializing cryptography after login...");
      const cryptoInitialized = await cryptoStore.initializeCryptography(data.access_token);
      if (!cryptoInitialized) {
        throw new Error("Failed to initialize cryptography");
      }

      websocketStore.connect();

      if (browser) {
        localStorage.setItem("authToken", data.access_token);
        localStorage.setItem("authUsername", username);
      }
      return true;
    } catch (e: any) {
      errorStore.setError(e.message, 401);
      console.error("Login error:", e);
      state.isAuthenticated = false;
      state.token = null;
      state.username = null;
      return false;
    }
  }

  async function register(usernameInput: string, passwordInput: string): Promise<boolean> {
    try {
      await registerUser(usernameInput, await hashPassword(passwordInput));
    } catch (error) {
      console.error("Registration failed:", error);
      throw error;
    }
  }

  function logout() {
    state.token = null;
    state.username = null;
    state.isAuthenticated = false;
    websocketStore.disconnect();
    cryptoStore.reset();
    chatStore.reset();
    if (browser) {
      localStorage.removeItem("authToken");
      localStorage.removeItem("authUsername");
    }
  }

  return {
    get current() {
      return state;
    },
    login,
    register,
    logout,
  };
}

export const authStore = createAuthStore();
