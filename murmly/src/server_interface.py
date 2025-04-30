import threading
import paramiko
import logging

from paramiko.common import (
    AUTH_FAILED,
    AUTH_SUCCESSFUL,
    OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
    OPEN_SUCCEEDED,
)

import db_utils

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


class Server(paramiko.ServerInterface):
    def __init__(self, client_address, db_conn):
        self.client_address = client_address
        self.db_conn = db_conn
        self.event = threading.Event()
        self.username = None
        self.channel = None

    def get_allowed_auths(self, username: str) -> str:
        return "publickey"

    def check_channel_request(self, kind: str, chanid):
        if kind == "session":
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    # def check_auth_password(self, username: str, password: str):
    #     logging.warning(f"Password auth attempt for '{username}' (disabled)")

    def check_auth_publickey(self, username: str, key: paramiko.PKey):
        logging.info(
            f"Attempting public key auth for user '{username}' from {self.client_address}"
        )
        return AUTH_SUCCESSFUL

        key_bytes = key.asbytes()

        if db_utils.authenticate_user_by_key_sync(self.db_conn, username, key_bytes):
            logging.info(f"Public key auth succeeded for user '{username}'")
            self.username = username
            return AUTH_SUCCESSFUL
        logging.warning(f"Public key auth failed for user '{username}'")
        return AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.channel = channel
        self.event.set()
        return True

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        # Clients like OpenSSH request a PTY, approve it
        return True
