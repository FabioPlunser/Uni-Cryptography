import socket
import threading
import paramiko
import sqlite3
import asyncio
import os
import base64
import haslib
import logging

from chat_app_interface import ChatInterface
import db_utils
import crypto_utils

HOST = "0.0.0.0"
PORT = 22
DATABASE_FILE = "murmly.db"
HOST_KEY_FILE = "server_host_key.pem"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# --- Global Variables ---
user_message_queues = {}
user_message_queues_lock = threading.Lock()
active_channels = {}
active_channels_lock = threading.Lock()


class Server(paramiko.ServerInterface):
    def __init__(self, client_address, db_conn):
        self.client_address = client_address
        self.db_conn = db_conn
        self.event = threading.Event()
        self.username = None
        self.channel = None

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    # Disable password authentication only use public key authentication
    def check_auth_password(self, username, password):
        logging.warning(f"Password auth attempt for '{username}' (disabled)")
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        logging.info(
            f"Attempting public key auth for user '{username}' from {self.client_address}"
        )

        key_bytes = key.asbytes()

        if db_utils.authenticate_user_by_key(self.db_conn, username, key_bytes):
            logging.info(f"Public key auth succeeded for user '{username}'")
            self.username = username
            return paramiko.AUTH_SUCCESSFUL
        logging.warning(f"Public key auth failed for user '{username}'")
        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.channel = channel
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        # Clients like OpenSSH request a PTY, approve it
        return True


# Client Handling Lgic
def handle_client(client_socket, client_address, db_conn, host_key):
    """Handles a single client connection."""
    logging.info(f"Accepted connection from {client_address}")
    try:
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)
        transport.local_version = "SSH-2.0-MurmlyChatServer1.0"  # Optional Identifier

        server_instance = Server(client_address, db_conn)
        transport.start_server(server=server_instance)

        logging.info(f"Waiting for auth from {client_address}...")

        auth_event_happened = server_instance.event.wait(10)

        if auth_event_happened and server_instance.username and server_instance.channel:
            username = server_instance.username
            channel = server_instance.channel
            logging.info(f"User '{username}' authenticated successfully.")

            # Add user to active channels
            with active_channels_lock:
                if username not in active_channels:
                    active_channels[username] = channel
                    logging.info(f"User '{username}' added to active channels.")
    except paramiko.SSHException as e:
        logging.error(f"SSH error: {e}")
    except Exception as e:
        logging.error(f"Error handling client {client_address}: {e}")


async def main():
    try:
        host_key = paramiko.RSAKey(filename=HOST_KEY_FILE)
        logging.info(f"Host key loaded from {HOST_KEY_FILE}")
    except IOError:
        logging.error(
            f"Failed to load host key from {HOST_KEY_FILE}. Generating a new one."
        )
        host_key = paramiko.RSAKey.generate(2048)
        host_key.write_private_key_file(HOST_KEY_FILE)
        logging.info(f"Host key generated and saved to {HOST_KEY_FILE}")

    # --- Database Initialization ---
    db = db_utils.Database()
    await db.init_db()
    db.mark_all_users_as_offline()

    # --- Start Server Socket ---
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        logging.info(f"Murmly server listening on {HOST}:{PORT}")
    except Exception as e:
        logging.error(f"Failed to bind or listen on {HOST}:{PORT}: {e}")
        return

    # --- Accept Connections Loop ---
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            db = db_utils.Database()
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address, db, host_key),
                daemon=True,
            )
            client_thread.start()
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
    finally:
        logging.info("Closing server socket.")
        server_socket.close()


if __name__ == "__main__":
    main()
