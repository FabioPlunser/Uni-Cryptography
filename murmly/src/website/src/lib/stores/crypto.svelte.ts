import { errorStore } from "./error.svelte";
import { authStore } from "./auth.svelte";

const ROTATION_THRESHOLD = 10;

import {
  type DHParameters,
  type DHPublicKey,
  type DHPrivateKey,
  deserializeDhParameters,
  generateDhKeyPair,
  serializeDhPublicKey,
  deserializeDhPublicKey,
  serializeDhPrivateKey,
  deriveSharedSecret as deriveSharedSecretUtil,
  encryptMessage,
  decryptMessage,
  deserializeDhPrivateKey,
} from "$lib/crypto";

// Get API URL from environment, fallback to relative path in production
const API_URL = import.meta.env.VITE_API_URL || '';

interface CryptoState {
  dhParams: DHParameters | null;
  myDhPrivateKey: DHPrivateKey | null;
  myDhPublicKey: DHPublicKey | null;
  peerSharedSecrets: Map<number, CryptoKey>;
  peerMessageNumbers: Map<number, number>;
  peerSharedSecretHistory: Map<number, Map<number, CryptoKey>>;
  peerKeyRotation: Map<number, { currentKey: CryptoKey, keyHistory: Map<number, CryptoKey>, messageCounter: number }>;
}

function createCryptoStore() {
  let state = $state<CryptoState>({
    dhParams: null,
    myDhPrivateKey: null,
    myDhPublicKey: null,
    peerSharedSecrets: new Map(),
    peerMessageNumbers: new Map(),
    peerSharedSecretHistory: new Map(),
    peerKeyRotation: new Map()
  });

  /**
   * Fetches the DH parameters from the server.
   * @returns A promise that resolves to true if the DH parameters are fetched and deserialized successfully, or false otherwise.
   */
  async function fetchDHParametersFromServer(): Promise<boolean> {
    try {
      const response = await fetch(`${API_URL}/dh_params_js`);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to fetch DH parameters");
      }
      const paramsJson = await response.json();
      state.dhParams = deserializeDhParameters(JSON.stringify(paramsJson));
      return true;
    } catch (e: any) {
      errorStore.setError(`DH Params Load: ${e.message}`, 400);
      console.error("fetchDHParametersFromServer error:", e);
      return false;
    }
  }

  /**
   * Generates a new DH key pair for the local user.
   * @returns A promise that resolves to true if the key pair is generated successfully, or false otherwise.
   */
  function generateUserDhKeys(): boolean {
    if (!state.dhParams) {
      errorStore.setError("DH parameters not loaded. Cannot generate keys.", 400);
      return false;
    }
    try {
      const { privKey, pubKey } = generateDhKeyPair(state.dhParams);
      state.myDhPrivateKey = privKey;
      state.myDhPublicKey = pubKey;
      return true;
    } catch (e: any) {
      errorStore.setError(`User DH key generation failed: ${e.message}`, 400);
      console.error("generateUserDhKeys error:", e);
      return false;
    }
  }

  /**
   * Uploads the user's public key to the server.
   * @param token - The authentication token.
   * @returns A promise that resolves to true if the public key is uploaded successfully, or false otherwise.
   */
  async function uploadPublicKey(token: string): Promise<boolean> {
    if (!state.myDhPublicKey) {
      errorStore.setError("User public key not generated. Cannot upload.", 400);
      return false;
    }
    try {
      const serializedPublicKey = serializeDhPublicKey(state.myDhPublicKey);
      const response = await fetch(`${API_URL}/update_public_key`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ public_key: serializedPublicKey }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to upload public key");
      }
      return true;
    } catch (e: any) {
      errorStore.setError(`Upload Public Key: ${e.message}`, "Crypto Error");
      console.error("uploadPublicKey error:", e);
      return false;
    }
  }

  /**
   * Initializes the cryptography.
   * @param token - The authentication token.
   * @returns A promise that resolves to true if the cryptography is initialized successfully, or false otherwise.
   */
  async function initializeCryptography(token: string): Promise<boolean> {
    if (!await fetchDHParametersFromServer()) return false;
    if (!generateUserDhKeys()) return false;
    if (!await uploadPublicKey(token)) return false;
    return true;
  }

  /**
   * Initializes the chat with a peer user.
   * @param peerUserId - The ID of the peer user.
   */
  async function initializeChat(peerUserId: number) {
    const token = authStore.current.token;
    if (!token) {
      console.warn("initializeChat called without a token.");
      return;
    }

    // Initialize crypto state if needed
    if (!state.dhParams || !state.myDhPrivateKey || !state.myDhPublicKey) {
      const initialized = await initializeCryptography(token);
      if (!initialized) {
        errorStore.setError('Failed to initialize cryptography', 'Crypto Error');
        return;
      }
    }

    const success = await ensureSecureChannel(token, peerUserId);
    if (!success) {
      errorStore.setError(`Failed to establish secure channel with ${peerUserId}.`, "Crypto Error");
      return;
    }
  }

  /**
   * Ensures a secure channel is established between the local user and a peer user.
   * @param token - The authentication token.
   * @param peerUserId - The ID of the peer user.
   * @returns A promise that resolves to true if the secure channel is established, or false otherwise.
   */
  async function ensureSecureChannel(token: string, peerUserId: number): Promise<boolean> {
    if (!state.dhParams) {
      const paramsLoaded = await fetchDHParametersFromServer();
      if (!paramsLoaded) {
        errorStore.setError('Failed to load DH parameters', 'Crypto Error');
        return false;
      }
    }

    if (!state.myDhPrivateKey || !state.myDhPublicKey) {
      const keysGenerated = generateUserDhKeys();
      if (!keysGenerated) {
        errorStore.setError('Failed to generate DH key pair', 'Crypto Error');
        return false;
      }
      // If keys were just generated, ensure the public key is uploaded.
      if (token && !await uploadPublicKey(token)) {
        console.warn("Failed to upload newly generated public key in ensureSecureChannel");
      }
    }

    try {
      // If we don't have a shared secret, establish one
      if (!state.peerKeyRotation.has(peerUserId)) {
        if (!state.myDhPrivateKey) {
          errorStore.setError('Own private key missing when trying to establish initial secret.', 'Crypto Error');
          console.error("CRITICAL: Own private key is null in ensureSecureChannel when trying to derive initial secret.");
          return false;
        }
        // Fetch peer's current public key
        const peerPubKey = await fetchPeerPublicKey(token, peerUserId);
        // Derive shared secret using THIS client's CURRENT private key and peer's public key
        const sessionKey = await deriveSharedSecretUtil(state.myDhPrivateKey, peerPubKey);
        state.peerKeyRotation.set(peerUserId, {
          currentKey: sessionKey,
          keyHistory: new Map(),
          messageCounter: 0
        });

        // Initialize message number tracking if not exists
        if (!state.peerMessageNumbers.has(peerUserId)) {
          state.peerMessageNumbers.set(peerUserId, 0);
        }

        // Initialize shared secret history if not exists
        if (!state.peerSharedSecretHistory.has(peerUserId)) {
          state.peerSharedSecretHistory.set(peerUserId, new Map());
        }

        // Store the current shared secret in history with current message number
        const currentMsgNum = state.peerMessageNumbers.get(peerUserId) || 0;
        state.peerSharedSecretHistory.get(peerUserId)?.set(currentMsgNum, sessionKey);
      }
      console.log("Secure channel established with", peerUserId, state.peerKeyRotation.get(peerUserId)?.currentKey);
      return true;
    } catch (error: any) {
      errorStore.setError(`Failed to establish secure channel with ${peerUserId}: ${error.message}`, 'Crypto Error');
      console.error(`ensureSecureChannel error with peer ${peerUserId}:`, error);
      return false;
    }
  }

  /**
   * Fetches the public key of a peer user from the server.
   * @param token - The authentication token.
   * @param peerUserId - The ID of the peer user.
   * @returns A promise that resolves to the peer's public key as a DHPublicKey object.
   */
  async function fetchPeerPublicKey(token: string, peerUserId: number): Promise<DHPublicKey> {
    const response = await fetch(`${API_URL}/users/${peerUserId}/public_key`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch peer public key: ${response.statusText}`);
    }
    const peerKeyResponse = await response.json();
    if (!peerKeyResponse.public_key) {
      throw new Error(`Public key for ${peerUserId} is null or not found.`);
    }
    if (!state.dhParams) {
      errorStore.setError('DH parameters not loaded. Cannot deserialize peer public key.', 'Crypto Error');
      throw new Error('DH parameters not loaded. Cannot deserialize peer public key.');
    }
    return deserializeDhPublicKey(peerKeyResponse.public_key, state.dhParams);
  }

  async function deriveNextKey(currentKey: CryptoKey) {
    const salt = window.crypto.getRandomValues(new Uint8Array(32));
    // Derive a new key using HKDF
    return await window.crypto.subtle.deriveKey(
      {
        name: "HKDF",
        salt,
        info: new TextEncoder().encode("key-rotation"),
        hash: "SHA-256",
      },
      currentKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }

  function reset() {
    state.dhParams = null;
    state.myDhPrivateKey = null;
    state.myDhPublicKey = null;
    state.peerSharedSecrets = new Map();
    state.peerMessageNumbers = new Map();
    state.peerSharedSecretHistory = new Map();
  }

  /**
   * Encrypts a message using the shared secret for a peer user.
   * @param peerUserId - The ID of the peer user.
   * @param message - The message to encrypt.
   * @returns A promise that resolves to the encrypted message as a base64 string.
   */
  async function encryptWSMessage(peerUserId: number, message: string): Promise<string> {
    let peerData = state.peerKeyRotation.get(peerUserId);
    if (!peerData) {
      errorStore.setError(`No shared secret found for peer ${peerUserId}. Cannot encrypt message.`, 'Crypto Error');
      peerData = {
        currentKey: state.peerSharedSecrets.get(peerUserId)!,
        keyHistory: new Map(),
        messageCounter: 0
      };
      state.peerKeyRotation.set(peerUserId, peerData);
    }

    try {
      // Increment message number for this peer
      const currentMsgNum = state.peerMessageNumbers.get(peerUserId) || 0;
      state.peerMessageNumbers.set(peerUserId, currentMsgNum + 1);

      // Store the current shared secret in history
      if (!state.peerSharedSecretHistory.has(peerUserId)) {
        state.peerSharedSecretHistory.set(peerUserId, new Map());
      }
      state.peerSharedSecretHistory.get(peerUserId)?.set(currentMsgNum, peerData.currentKey);

      peerData.messageCounter++;
      if (peerData.messageCounter % ROTATION_THRESHOLD === 0) {
        const aesKey = await deriveNextKey(peerData.currentKey);
        peerData.currentKey = aesKey;
        peerData.keyHistory.set(peerData.messageCounter, aesKey);
      }
      return encryptMessage(peerData.currentKey, message);
    } catch (e: any) {
      errorStore.setError(`Failed to encrypt message: ${e.message}`, 'Crypto Error');
      return '';
    }
  }

  /**
   * Decrypts a message using the shared secret for a peer user.
   * @param peerUserId - The ID of the peer user.
   * @param message - The message to decrypt.
   * @param messageNumber - The message number of the message to decrypt.
   * @returns A promise that resolves to the decrypted message as a string.
   */
  async function decryptWSMessage(peerUserId: number, message: string, messageNumber?: number): Promise<string> {
    let peerData = state.peerKeyRotation.get(peerUserId);
    if (!peerData) {
      errorStore.setError(`No shared secret found for peer ${peerUserId}. Cannot decrypt message.`, 'Crypto Error');
      return '';
    }

    const key = messageNumber !== undefined
      ? peerData.keyHistory.get(messageNumber)
      : peerData.currentKey;

    if (!key) {
      errorStore.setError(`No shared secret found for peer ${peerUserId}. Cannot decrypt message.`, 'Crypto Error');
      return '';
    }

    console.log("Decrypting message with key:", key);

    try {
      return decryptMessage(key, message);
    } catch (e: any) {
      errorStore.setError(`Failed to decrypt message: ${e.message}`, 'Crypto Error');
      return '';
    }
  }

  return {
    get currentDhParams() { return state.dhParams; },
    get currentUserPubKey() { return state.myDhPublicKey; },
    initializeCryptography,
    initializeChat,
    ensureSecureChannel,
    encryptWSMessage,
    decryptWSMessage,
    reset
  };
}
export const cryptoStore = createCryptoStore();
