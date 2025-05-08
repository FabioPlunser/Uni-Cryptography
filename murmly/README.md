# Murmly - Secure Chat Application

A complete End-to-End Encrypted (E2EE) chat application built with Python, featuring both a CLI client and a web interface.

## Features

Murmly provides strong end-to-end encryption for all messages using Diffie-Hellman key exchange and AES-GCM encryption. The server acts only as a message router and never has access to decrypted content. 

You can interact with Murmly through either the command-line interface, a rich terminal UI built with Textual, or the modern web interface created with SvelteKit and Tailwind CSS.

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
<!-- still TODO: -->

```bash
cd src/website
npm install (???)
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

### Web Interface

For those who prefer a graphical interface, the web client offers a modern UI. Start it by navigating to the `src/website` directory and running:

```bash
npm run dev
```

This launches the development server, usually at `http://localhost:5173`. Open this address in your browser to access the web interface where you can register, log in, and start chatting securely.

