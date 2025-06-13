export function hexToUint8Array(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  // Create a Uint8Array view of the buffer
  const bytes = new Uint8Array(buffer);

  // Use a more robust approach with mapping
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }

  // Use standard base64 encoding
  return btoa(binary);
}

export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  try {
    // Decode base64 to binary string
    const binaryString = atob(base64);

    // Create buffer with correct length
    const bytes = new Uint8Array(binaryString.length);

    // Fill the buffer byte by byte
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    return bytes.buffer;
  } catch (e) {
    console.error('Error decoding base64:', e, 'Original string:', base64);
    throw e;
  }
}


export interface DHParameters {
  p: bigint;
  g: bigint;
}

export interface DHPublicKey {
  y: bigint;
  params: DHParameters;
}

export interface DHPrivateKey {
  x: bigint;
  params: DHParameters;
}

export function deserializeDhParameters(serializedParams: string): DHParameters {
  const params = JSON.parse(serializedParams);
  return {
    p: BigInt(`0x${params.p_hex}`),
    g: BigInt(`0x${params.g_hex}`),
  };
}

export function generateDhKeyPair(params: DHParameters): {
  privKey: DHPrivateKey;
  pubKey: DHPublicKey;
} {
  const x = BigInt(
    Math.floor(Math.random() * Number(params.p - 2n)) + 1
  );

  const y = power(params.g, x, params.p); // g^x mod p

  return {
    privKey: { x, params },
    pubKey: { y, params },
  };
}

function power(base: bigint, exp: bigint, mod: bigint): bigint {
  let res = 1n;
  base = base % mod;
  while (exp > 0n) {
    if (exp % 2n === 1n) res = (res * base) % mod;
    base = (base * base) % mod;
    exp = exp / 2n;
  }
  return res;
}

export function serializeDhPublicKey(pubKey: DHPublicKey): string {
  return JSON.stringify({ y_hex: pubKey.y.toString(16) });
}

export async function deriveSharedSecret(
  privKey: DHPrivateKey,
  peerPubKey: DHPublicKey
): Promise<CryptoKey> {
  // Shared secret: (peer_pub_key.y ^ my_priv_key.x) mod p
  const sharedSecretBigInt = power(peerPubKey.y, privKey.x, privKey.params.p);

  // Convert BigInt shared secret to ArrayBuffer
  let hex = sharedSecretBigInt.toString(16);
  if (hex.length % 2) hex = "0" + hex;
  const sharedSecretBytes = new Uint8Array(hex.match(/.{1,2}/g)!.map((byte) => parseInt(byte, 16)));

  // Import the shared secret as a raw key for HKDF
  const sharedSecretKey = await window.crypto.subtle.importKey(
    "raw",
    sharedSecretBytes.buffer,
    { name: "HKDF" },
    false,
    ["deriveKey"]
  );

  // Use HKDF to derive the AES key, matching the server's implementation
  const derivedKey = await window.crypto.subtle.deriveKey(
    {
      name: "HKDF",
      salt: new Uint8Array(0), // Empty array equivalent to Python's None
      info: new TextEncoder().encode("handshake data"),
      hash: "SHA-256",
    },
    sharedSecretKey,
    { name: "AES-GCM", length: 256 }, // 256 bits = 32 bytes, matching Python's length=32
    false,
    ["encrypt", "decrypt"]
  );
  return derivedKey;
}

// --- AES-GCM Encryption/Decryption ---
const AES_IV_LENGTH = 12; // Bytes for AES-GCM IV (96 bits is common)

export async function encryptMessage(
  aesKey: CryptoKey,
  plaintext: string
): Promise<string> {
  const iv = window.crypto.getRandomValues(new Uint8Array(AES_IV_LENGTH));
  const encodedPlaintext = new TextEncoder().encode(plaintext);

  const ciphertext = await window.crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv },
    aesKey,
    encodedPlaintext
  );

  // Prepend IV to ciphertext for storage/transmission
  const ivAndCiphertext = new Uint8Array(iv.length + ciphertext.byteLength);
  ivAndCiphertext.set(iv, 0);
  ivAndCiphertext.set(new Uint8Array(ciphertext), iv.length);

  return arrayBufferToBase64(ivAndCiphertext.buffer);
}

export async function decryptMessage(
  aesKey: CryptoKey,
  base64IvAndCiphertext: string
): Promise<string> {
  try {

    // Log the base64 string characteristics
    const ivAndCiphertext = new Uint8Array(base64ToArrayBuffer(base64IvAndCiphertext));

    if (ivAndCiphertext.length <= AES_IV_LENGTH) {
      throw new Error(`Message too short: ${ivAndCiphertext.length} bytes (need more than IV length of ${AES_IV_LENGTH})`);
    }

    // Extract IV and ciphertext
    const iv = ivAndCiphertext.slice(0, AES_IV_LENGTH);
    const ciphertext = ivAndCiphertext.slice(AES_IV_LENGTH);

    if (ciphertext.length === 0) {
      throw new Error("Ciphertext is empty after IV extraction");
    }

    const decryptedBuffer = await window.crypto.subtle.decrypt(
      { name: "AES-GCM", iv: iv },
      aesKey,
      ciphertext
    );

    const decoded = new TextDecoder().decode(decryptedBuffer);
    return decoded;
  } catch (error) {
    console.error("Decryption error details:", {
      error,
      message: base64IvAndCiphertext,
      messageLength: base64IvAndCiphertext.length
    });
    throw error;
  }
}
export interface DeserializedPeerPublicKey {
  y: bigint;
}

export function deserializeDhPublicKey(
  serializedPubKey: string,
  params: DHParameters
): DHPublicKey {
  // Assumes serializedPubKey is a JSON string like: {"y_hex":"..."}
  const pubKeyData = JSON.parse(serializedPubKey);
  if (typeof pubKeyData.y_hex !== "string") {
    throw new Error("Invalid serialized public key format: missing y_hex string.");
  }
  return {
    y: BigInt(`0x${pubKeyData.y_hex}`),
    params: params,
  };

}

export function serializeDhPrivateKey(privKey: DHPrivateKey): string {
  return JSON.stringify({ x_hex: privKey.x.toString(16) });
}

export function deserializeDhPrivateKey(serializedPrivKey: string, params: DHParameters): DHPrivateKey {
  const privKeyData = JSON.parse(serializedPrivKey);
  if (typeof privKeyData.x_hex !== "string") {
    throw new Error("Invalid serialized private key format: missing x_hex string.");
  }
  return {
    x: BigInt(`0x${privKeyData.x_hex}`),
    params: params,
  };
}