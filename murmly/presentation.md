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
## Cryptography

<!-- When client is connected to server, it asks for public key of the other client -->
- Client logs in/registers, gets Diffie-Hellman parameters from server
- Creates private and public key, uploads public key to server
- Tries to establish secure connection with other client by performing key exchange
- If key exchange is successful, the client will generate a symmetric key using the shared secret
$\Rightarrow$ symmetric encryption (AES-GCM)

---
<center>
  <img src="./message_flow.png" width=950>
</center>


---

## Key Exchange: Diffie-Hellman details

```python 
# on server
def generate_dh_parameters():
    parameters: DHParameters = dh.generate_parameters(generator=2, key_size=PRIME_BITS)
    return parameters

# on client
def exchange_and_derive(priv_key: DHPrivateKey, peer_pub_key: DHPublicKey) -> bytes:
    # the peer_pub_key is B= g^{peer_private_key} mod p
    # the shared key is A=B^{priv_key} mod p
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
- Simpler solution than in last project


---
<!-- ## Key Rotation 

- Key $k_1$ encrypts messages $m_i \in \{m_1, ..., m_100\}$
- Key $k_2$ encrypts messages $m_{j} \in \{m_{101}, ..., m_{200}\}$

- if attacker compromises key $k_1$, they can only decrypt messages $m_i$ and not $m_j$.

$\Rightarrow$ leaking a key does not leak previous keys!

---

## Key Rotation  - Details
- *forward* and *backward* rotation
- rotated after 100 messages to reduce risk of key compromise
- If current key is compromised, past messages remain secure

```python
def rotate_key(self) -> tuple[bytes, bytes]:
    """Rotate the key for forward secrecy."""
    new_key, salt = derive_next_key(self.current_key)
    self.key_history.append((self.current_key, salt))
    self.current_key = new_key
    self.message_counter = 0
    return new_key, salt
```

--- -->

## Additional: Full browser client

- Implemented a web browser client using SvelteKit (JavaScript framework)
- Implements its own cryptography implementation, similar to the Python implementation
- Challenge: Ensuring cross-platform compatibility

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
## What didn't work

- Chat history
- Web client in JavaScript/Svelte communication with Python client - did not work


---

## Lessons learned
- Python implementation with simple CLI tool was relatively easy to implement
- Browser client was more challenging due to interoperability issues between CLI and JavaScript 
  - Used most of our development time
  - Affected our final submission

---
## Demo

Let's see it in action!