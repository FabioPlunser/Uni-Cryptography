export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}



export function base64ToArrayBuffer(base64: string): ArrayBuffer { const binary_string = window.atob(base64);
  const len = binary_string.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binary_string.charCodeAt(i);
  }
  return bytes.buffer;
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
  if (hex.length % 2) {
    hex = "0" + hex;
  } // Ensure even length for Buffer.from
  const sharedSecretBytes = new Uint8Array(
    hex.match(/.{1,2}/g)!.map((byte) => parseInt(byte, 16))
  );

  // Use HKDF or SHA-256 to derive a fixed-size AES key
  // For simplicity, using SHA-256 directly on the shared secret bytes.
  // In a real app, use HKDF (RFC 5869).
  const aesKeyMaterial = await window.crypto.subtle.digest(
    "SHA-256",
    sharedSecretBytes.buffer
  );

  // Import this material as an AES-GCM key
  return window.crypto.subtle.importKey(
    "raw",
    aesKeyMaterial,
    { name: "AES-GCM" },
    false, // not extractable
    ["encrypt", "decrypt"]
  );
}

// --- AES-GCM Encryption/Decryption ---
const AES_IV_LENGTH = 12; // Bytes for AES-GCM IV (96 bits is common)

export async function encryptMessage(
  aesKey: CryptoKey,
  plaintext: string
): Promise<string> { // Returns Base64 encoded (IV + Ciphertext)
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
  const ivAndCiphertext = base64ToArrayBuffer(base64IvAndCiphertext);

  const iv = ivAndCiphertext.slice(0, AES_IV_LENGTH);
  const ciphertext = ivAndCiphertext.slice(AES_IV_LENGTH);

  const decryptedBuffer = await window.crypto.subtle.decrypt(
    { name: "AES-GCM", iv: new Uint8Array(iv) }, // Ensure iv is Uint8Array
    aesKey,
    ciphertext
  );

  return new TextDecoder().decode(decryptedBuffer);
}
