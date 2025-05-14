---
marp: true
class:
---

# Murmly - E2EE Messaging
by Fabio Plunser, Cedric Sillaber

---

## Our approach

- RESTful server using **FastAPI**
  - User authentication
  - Public key storage
  - Message routing only (no access to content)
- **WebSockets** for real-time messaging
- Python CLI client with `cryptography` library
- *in addition*: Full browser client (SvelteKit) with Web Crypto API


---
## Cryptography Theory

When client is connected to server, it asks for public key of the other client
- Tries to establish secure connection with other client and performing key exchange
- If key exchange is successful, the client will generate a symmetric key using the shared secret
$\Rightarrow$ symmetric encryption (AES-GCM)

---
## Message Flow

![message flow](./message_flow.png)
<figure>
  <img src="./message_flow.png" width=300>
</figure>

---

## Key Exchange: Diffie Hellman details

```python 
# Server-side implementation in crypto_utils.py
def generate_dh_parameters():
    parameters: DHParameters = dh.generate_parameters(generator=2, key_size=PRIME_BITS)
    return parameters

def exchange_and_derive(priv_key: DHPrivateKey, peer_pub_key: DHPublicKey) -> bytes:
    shared_key: bytes = priv_key.exchange(peer_public_key=peer_pub_key)
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"handshake data",
    ).derive(shared_key)
    return derived_key
``` 


---

## AES-GCM Implementation

```python
def encrypt_aes_gcm(key: bytes, data: bytes, associated_data: bytes = None) -> bytes:
    # Generate random 12-byte nonce
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    
    # Encrypt with AES-GCM
    ct = aesgcm.encrypt(
        nonce=nonce,
        data=data,
        associated_data=associated_data,
    )
    # Return nonce + ciphertext
    return nonce + ct
```

- Provides both **confidentiality** and **authenticity**
- Each message uses a unique IV (nonce)


---

## Additional: Full browser client

we ....

---

## Additional: Web Client Cryptography
```typescript
export async function deriveSharedSecret(
  privKey: DHPrivateKey,
  peerPubKey: DHPublicKey
): Promise<CryptoKey> {
  // Shared secret: (peer_pub_key.y ^ my_priv_key.x) mod p
  const sharedSecretBigInt = power(peerPubKey.y, privKey.x, privKey.params.p);
  
  // Derive key using HKDF (same as Python implementation)
  return window.crypto.subtle.deriveKey(
    {
      name: "HKDF",
      salt: new Uint8Array(0),
      info: new TextEncoder().encode("handshake data"),
      hash: "SHA-256",
    },
    importedKey,
    { name: "AES-GCM", length: 256 },
    false, ["encrypt", "decrypt"]
  );
}
```

---
## Demo

Let's see it in action!



--- 

## what didn't work

- chat history