# Security Implementation Details

## Authentication and E2EE Communication

### User Authentication
- Implemented in `server.py` using JWT tokens
- Users must authenticate before accessing any secure endpoints
- Authentication token is required for all API calls

### Initial Key Exchange
When User A starts communication with User B:

1. **DH Parameters Exchange**
   - Server provides DH parameters (prime number and generator)
   - Implemented in `server.py` endpoint `/dh_params`
   - Parameters are used to establish a secure channel

2. **Public Key Exchange**
   - Each user generates a DH key pair
   - Public keys are stored on the server
   - Implemented in `website/src/lib/stores/crypto.svelte.ts`:
     ```typescript
     async function uploadPublicKey(token: string)
     async function fetchPeerPublicKey(token: string, peerUserId: number)
     ```

3. **Shared Secret Derivation**
   - Implemented in `website/src/lib/crypto.ts`:
     ```typescript
     export async function deriveSharedSecret(
       privKey: DHPrivateKey,
       peerPubKey: DHPublicKey
     )
     ```
   - Uses DH key exchange to establish a shared secret
   - HKDF is used to strengthen the derived key

## Message Encryption

### Symmetric Encryption
- Uses AES-GCM for message encryption
- Implemented in `website/src/lib/crypto.ts`:
  ```typescript
  export async function encryptMessage(
    aesKey: CryptoKey,
    plaintext: string
  )
  ```
- Each message uses a unique IV (Initialization Vector)
- Provides both confidentiality and authenticity

## Key Rotation and Secrecy

### Backward Secrecy
Prevents recovery of future keys if a current key is compromised.

Implemented in `crypto_utils.py`:
```python
class KeyRotationManager:
    def __init__(self, initial_key: bytes):
        self.current_key = initial_key
        self.key_history = []  # List of (key, salt) tuples
        self.message_counter = 0
        self.ROTATION_THRESHOLD = 100  # Rotate key after 100 messages
```

Key features:
- Keys are rotated after every 100 messages
- Uses HKDF with unique salts for each rotation
- Old keys are not stored, making it impossible to derive future keys
- Efficient implementation with minimal overhead

### Forward Secrecy
Prevents recovery of past messages if a current key is compromised.

Implemented through:
1. **DH Key Exchange**
   - New DH key pairs for each session
   - Private keys are deleted after use
   - Implemented in `website/src/lib/crypto.ts`:
     ```typescript
     export function generateDhKeyPair(params: DHParameters)
     ```

2. **Key Management**
   - Each peer has a separate shared secret
   - Keys are stored in `peerSharedSecrets` Map
   - Implemented in `website/src/lib/stores/crypto.svelte.ts`:
     ```typescript
     async function ensureSecureChannel(token: string, peerUserId: number)
     ```

## Security Features

### Key Storage
- Private keys are never stored on the server
- Public keys are stored securely in the database
- Shared secrets are kept in memory only
- Local storage is used for DH parameters and public keys

### Key Rotation
- Automatic key rotation after 100 messages
- Uses cryptographically secure random number generation
- Implements both forward and backward secrecy
- Minimal communication overhead

### Message Security
- Each message is encrypted with a unique IV
- AES-GCM provides both encryption and authentication
- Messages cannot be tampered with or read by unauthorized parties
- Perfect forward secrecy ensures past messages remain secure

## Implementation Efficiency

The implementation is designed to be efficient while maintaining security:

1. **Key Rotation**
   - Uses HKDF which is computationally cheap
   - Only rotates after 100 messages
   - Minimal memory overhead

2. **Key Exchange**
   - DH key exchange only performed when needed
   - Public keys cached on server
   - Efficient key derivation using HKDF

3. **Message Encryption**
   - AES-GCM is fast and secure
   - Unique IVs generated efficiently
   - Minimal overhead per message

## Verification

You can verify the security features are working by:

1. **Backward Secrecy**
   - Send more than 100 messages
   - Check browser console for key rotation logs
   - Verify messages continue to be encrypted

2. **Forward Secrecy**
   - Check that new sessions use new DH key pairs
   - Verify old messages cannot be decrypted with new keys
   - Monitor key exchange process in browser console

3. **Message Security**
   - Verify messages are encrypted in transit
   - Check that only intended recipients can decrypt
   - Verify message integrity is maintained 