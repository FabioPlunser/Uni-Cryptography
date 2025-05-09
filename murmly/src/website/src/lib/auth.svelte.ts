import { browser } from "$app/environment";
import { loginForToken, registerUser } from "$lib/apis";

const initialAuthState: AuthState = {
  username: null,
  token: null,
  isAuthenticated: false,
};

function createAuthStore() {
  let state = $state<AuthState>(initialAuthState);

  if (browser) {
    const storedToken = localStorage.getItem("authToken");
    const storedUsername = localStorage.getItem("authUsername");
    if (storedToken && storedUsername) {
      state.token = storedToken;
      state.username = storedUsername;
      state.isAuthenticated = true;
    }
  }

  return {
    get current() {
      return state;
    },
    async login(usernameInput: string, passwordInput: string) {
      const formData = new URLSearchParams();
      formData.append("username", usernameInput);
      formData.append("password", passwordInput);
      try {
        const tokenData: Token = await loginForToken(formData);
        state.token = tokenData.access_token;
        state.username = usernameInput;
        state.isAuthenticated = true;
        if (browser) {
          localStorage.setItem("authToken", tokenData.access_token);
          localStorage.setItem("authUsername", usernameInput);
        }
        return true;
      } catch (error) {
        console.error("Login failed:", error);
        state.isAuthenticated = false;
        state.token = null;
        state.username = null;
        throw error;
      }
    },
    async register(usernameInput: string, passwordInput: string) {
      try {
        await registerUser(usernameInput, passwordInput);
        alert("Registration successful! Please log in.");
      } catch (error) {
        console.error("Registration failed:", error);
        throw error;
      }
    },
    logout() {
      state.token = null;
      state.username = null;
      state.isAuthenticated = false;
      if (browser) {
        localStorage.removeItem("authToken");
        localStorage.removeItem("authUsername");
      }
    },
  };
}

export const authStore = createAuthStore();
