import { error } from "./stores.svelte";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


async function hashPassword(password: string): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(password));
  return btoa(String.fromCharCode(...new Uint8Array(hash)));
}

export async function registerUser(username: string, password: string): Promise<String> {
  let hashedPassword = await hashPassword(password);
  let userData: UserCreate = {
    username: username,
    password: hashedPassword,
  };

  const response = await fetch(`${API_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userData),
  });
  if (!response.ok) {
    const errorData = await response.json();
    error.message = errorData.detail;
    error.code = response.status;
  }
  return response.json();
}

export async function loginForToken(
  formData: URLSearchParams
): Promise<Token> {
  const response = await fetch(`${API_URL}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json();
    error.message = errorData.detail;
    error.code = response.status;
  }
  return response.json();
}

export async function getDhParameters(token: string): Promise<string> {
  const response = await fetch(`${API_URL}/dh_params`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const errorData = await response.json();
    error.message = errorData.detail;
    error.code = response.status;
  }
  const data = await response.json();
  return data.params;
}

export async function updateUserPublicKey(
  publicKeyData: PublicKeyUpdateData,
  token: string
): Promise<any> {
  const response = await fetch(`${API_URL}/users/me/public_key`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(publicKeyData),
  });
  if (!response.ok) {
    const errorData = await response.json();
    error.message = errorData.detail;
    error.code = response.status;
  }
  return response.json();
}