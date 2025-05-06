# Murmly - Secure CLI Chat Application

A simple End-to-End Encrypted (E2EE) chat application built with Python, accessed via SSH.

## Features

*   **SSH-Based Access:** Users connect using standard SSH clients (`ssh <username>@<server_ip> -p <port>`).
*   **SSH Key Authentication:** Users are authenticated using their SSH public keys. (Auto-registration on first login might be enabled).
*   **Textual TUI:** A terminal user interface built with the Textual framework.
*   **Online User List:** See who else is currently connected.
*   **One-to-One E2EE:** Securely chat with another online user using Diffie-Hellman key exchange and AES-GCM encryption. The server only routes encrypted messages.
*   **No Group Chats:** Only one-to-one communication is supported.

## Technology Stack

*   **Python 3.x**
*   **Paramiko:** For the SSH server implementation.
*   **Textual:** For the Terminal User Interface (TUI).
*   **Cryptography:** For Diffie-Hellman, AES-GCM, hashing, and key derivation.
*   **SQLite:** For storing user information and potentially message metadata.

## Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)
*   An SSH client (like OpenSSH) installed on the user's machine.
*   Users need an SSH key pair (e.g., generated with `ssh-keygen`).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd murmly
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

*   **Host Key:** The server needs an SSH host key. If `server_key.pem` doesn't exist in the `murmly` directory when the server starts, it will automatically generate one.
*   **Port:** The server defaults to port `2222` in `src/server.py`. You can change this. Using port `22` requires running the server with `sudo`.
*   **Database:** The SQLite database file (`murmly.db`) will be created automatically in the `murmly` directory.

## Running the Server

Navigate to the `murmly` directory and run:

```bash
python src/server.py
```


## Logging in for the first time
In order to register for a user, you have to create a valid RSA-keypair for ssh. 

This is done using: 
```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa_murmly
```

This creates a `public, private` key pair used for the identification on the server.
To use those keys for identification, use: 

```bash
ssh -i ~/.ssh/id_rsa_murmly <username>@<server_ip> -p 2222
```

### Using our helper script

For testing purposes, we provide a simple provisioning script to make key management easier:

```bash
# Generate a new key for a username
./murmly.sh generate username1

# Connect to the server with that username
./murmly.sh connect username1
```

The script automatically handles key generation and storage in the `./keys/` directory, and uses the correct parameters when connecting to the server. Each user needs their own unique SSH key for authentication.