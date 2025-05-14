# Murmly - Secure Chat Application

A complete End-to-End Encrypted (E2EE) chat application built with Python, featuring both a CLI client and a web interface.

## Features

Murmly provides strong end-to-end encryption for all messages using Diffie-Hellman key exchange and AES-GCM encryption. The server acts only as a message router and never has access to decrypted content. 

You can interact with Murmly through either the command-line interface or the modern web interface created with SvelteKit and Tailwind CSS.

## Technology Stack

The application architecture consists of three main components:

The backend server is built with FastAPI, providing both REST APIs and WebSocket support. User data and message metadata are stored in SQLite, while authentication is handled through JWT tokens. The cryptography library handles Diffie-Hellman operations, AES-GCM encryption, and secure key derivation.

The CLI client is a python-based terminal application. 

The web client is developed with SvelteKit and styled with Tailwind CSS.

## Installation

Begin by cloning the repository and navigating to the project directory:

```bash
git clone https://github.com/FabioPlunser/Uni-Cryptography.git
cd murmly
```

Install the server and CLI dependencies with pip:

```bash
pip install -r requirements.txt
```

For the web interface: 
The website is built statically and then served by the FastAPI server.
```bash
cd src/website
bun install 
bun run build
```


## Configuration

The server is configured to run on `http://localhost:8000` by default, as specified in `src/config.py`. You can modify this setting to suit your needs. For development purposes, this is fine, but production environments should always use HTTPS.

When you first run the server, a SQLite database file (`murmly.db`) will be automatically created in the project directory to store user information and message metadata.

## Running the Application

### Server

To start the chat server, navigate to the `murmly` directory and run:

```bash
cd src
uvicorn server:app
```

This will launch the FastAPI server at `http://localhost:8000` (or your configured address).

### CLI Client

The command-line client can be started from the `murmly` directory with:

```bash
python src/client.py
```

This will register automatically at first launch.

Once connected, you can use several commands:
- Type `/users` to see who's currently online
- Start a message with `@username` to send it to a specific user
- Use `/help` to view all available commands
- Type `/quit` to exit the chat

### Web Interface Dev

For those who prefer a graphical interface, the web client offers a modern UI. Start it by navigating to the `src/website` directory and running:

```bash
bun run dev
```

This launches the development server, usually at `http://localhost:5173`. Open this address in your browser to access the web interface where you can register, log in, and start chatting securely.


# Implementation Details

## Authentication
- The application uses JWT (JSON Web Tokens) for authentication
- Users must register and login to get an access token
- The server validates tokens for all protected endpoints
- Tokens expire after a configurable time period (default 15 minutes)

## End-to-End Encryption Implementation
- Initial Key Exchange
- Uses Diffie-Hellman key exchange for secure key establishment
- Parameters are generated with a configurable prime bit length
- The server provides DH parameters to clients
- Each client generates their own key pair and exchanges public keys
- The shared secret is derived using HKDF (HMAC-based Key Derivation Function)

## Message Encryption
- Messages are encrypted using AES-GCM (Galois/Counter Mode)
- Each message uses a unique 12-byte nonce
- The encryption key is derived from the DH shared secret
- Messages include associated data for additional security

## Key Rotation (Optional Features)
- Implements forward and backward secrecy
- Rotates encryption keys after a configurable number of messages
- Uses HKDF for key derivation
- Maintains a history of used keys

## Key Rotation Implementation in Web Interface
### Forward Secrecy
The web interface implements forward secrecy through the `crypto.svelte.ts` store, which manages key rotation for each chat session. Here's how it works:

1. **Key Rotation Threshold**:
   - Keys are rotated after every 10 messages (defined by `ROTATION_THRESHOLD = 10`)
   - This is tracked per peer using the `peerKeyRotation` Map

2. **Key Derivation**:
   - When a new key is needed, it's derived using HKDF (Hash-based Key Derivation Function)
   - The current key is used as input to derive the next key
   - A new random salt is generated for each key rotation
   - The derived key is stored in the key history

3. **Key History Management**:
   - Each peer's key history is stored in `peerKeyRotation` Map
   - The structure includes:
     - `currentKey`: The active encryption key
     - `keyHistory`: Map of message numbers to keys
     - `messageCounter`: Tracks number of messages sent

### Backward Secrecy
Backward secrecy is implemented through the key history management system:

1. **Key Storage**:
   - Each key is stored in `peerSharedSecretHistory` with its associated message number
   - This allows decryption of old messages while maintaining security

2. **Message Number Tracking**:
   - Each message is assigned a unique number
   - The `peerMessageNumbers` Map tracks the current message number for each peer
   - When decrypting messages, the correct key is retrieved based on the message number

3. **Key Derivation Chain**:
   - Keys are derived in a way that prevents deriving previous keys from current ones
   - The HKDF function is used with a unique salt for each key
   - The salt is stored with the key history to allow decryption of old messages

### Implementation Details

1. **Key Rotation Process**:
```typescript
async function deriveNextKey(currentKey: CryptoKey) {
    // Generate new random salt
    const salt = crypto.getRandomValues(new Uint8Array(32));
    
    // Derive new key using HKDF
    const newKey = await crypto.subtle.deriveKey(
        {
            name: "HKDF",
            salt: salt,
            info: new TextEncoder().encode("forward_secrecy_rotation"),
            hash: "SHA-256",
        },
        currentKey,
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"]
    );
    
    return { newKey, salt };
}
```

2. **Message Encryption/Decryption**:
```typescript
async function encryptWSMessage(peerUserId: number, message: string): Promise<string> {
    const keyRotation = state.peerKeyRotation.get(peerUserId);
    if (!keyRotation) throw new Error("No key rotation found for peer");
    
    // Increment message counter and rotate key if needed
    keyRotation.messageCounter++;
    if (keyRotation.messageCounter >= ROTATION_THRESHOLD) {
        const { newKey, salt } = await deriveNextKey(keyRotation.currentKey);
        keyRotation.keyHistory.set(keyRotation.messageCounter, keyRotation.currentKey);
        keyRotation.currentKey = newKey;
        keyRotation.messageCounter = 0;
    }
    
    return encryptMessage(keyRotation.currentKey, message);
}
```

3. **Message Decryption with Key History**:
```typescript
async function decryptWSMessage(peerUserId: number, message: string, messageNumber?: number): Promise<string> {
    const keyRotation = state.peerKeyRotation.get(peerUserId);
    if (!keyRotation) throw new Error("No key rotation found for peer");
    
    // If message number is provided, use the appropriate historical key
    const key = messageNumber !== undefined 
        ? keyRotation.keyHistory.get(messageNumber) 
        : keyRotation.currentKey;
        
    if (!key) throw new Error("No key found for message number");
    
    return decryptMessage(key, message);
}
```

This implementation ensures that:
- Keys are regularly rotated to maintain forward secrecy
- Old messages can be decrypted using the appropriate historical key
- Compromising a current key doesn't reveal past or future keys
- The key rotation process is efficient and doesn't require additional communication overhead


# Additioanl Features which didn't work out 
Getting the chat history from the server.
Issues with decrypting messages. Not sure why decrypting exactly the same as with the 
websocket. 
It might be that the key rotation is not working as expected. 
