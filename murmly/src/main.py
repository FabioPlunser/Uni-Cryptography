import socket
import threading
import paramiko
import asyncio
import logging

import db_utils
from client_handler import handle_client

HOST = "0.0.0.0"
PORT = 2222
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


def main():
    # --- Database Initialization ---
    db = db_utils.Database()
    try:
        asyncio.run(db.init_db())
        asyncio.run(db.mark_all_offline())

    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        return

    # --- Load Host Key ---
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
                args=(
                    client_socket,
                    client_address,
                    host_key,
                    db,
                    active_channels,
                    active_channels_lock,
                    user_message_queues,
                    user_message_queues_lock,
                ),
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
