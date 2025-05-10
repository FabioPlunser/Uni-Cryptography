import { errorStore } from "./stores/error.svelte";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


export async function registerUser(username: string, password: string): Promise<String> {
  let userData: UserCreate = {
    username: username,
    password: password,
  };
  console.log("Registering user:", userData);

  const response = await fetch(`${API_URL}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userData),
  });
  const data = await response.json();
  if (!response.ok) {
    errorStore.setError(data.detail, data.status);
  }
  if (data.success) {
    alert("User registered successfully");
  }

  return data;
}

export async function loginForToken(
  formData: URLSearchParams
): Promise<Token> {
  const response = await fetch(`${API_URL}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) {
    errorStore.setError(data.detail, data.status);
    throw new Error("Login failed");
  }

  console.log("Token response:", data);
  return data;
}

export async function getDhParameters(token: string): Promise<string> {
  const response = await fetch(`${API_URL}/dh_params`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const errorData = await response.json();
    errorStore.setError(errorData.detail, response.status);
  }
  const data = await response.json();
  return data.params;
}

export async function updateUserPublicKey(
  publicKeyData: PublicKeyUpdateData,
  token: string
): Promise<any> {
  const response = await fetch(`${API_URL}/update_public_key`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(publicKeyData),
  });
  if (!response.ok) {
    const errorData = await response.json();
    errorStore.setError(errorData.detail, response.status);
  }
  return response.json();
}

export async function getOnlineUsers(token: string): Promise<User[]> {
  const response = await fetch(`${API_URL}/users/online`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  let data = await response.json();
  if (!response.ok) {
    errorStore.setError(data.detail, response.status);
  }
  return data
}
export async function getUserPublicKey(
  username: string,
  token: string
): Promise<string> {
  const response = await fetch(`${API_URL}/users/${username}/public_key`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const errorData = await response.json();
    errorStore.setError(errorData.detail, response.status);
  }
  const data = await response.json();
  return data.public_key;
}

export async function getPeerPublicKey(
  username: string,
  token: string
): Promise<PublicKeyResponse> {
  const response = await fetch(`${API_URL}/users/${username}/public_key`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const errorData = await response.json();
    errorStore.setError(errorData.detail, response.status);
  }
  const data = await response.json();
  return data;
}   
