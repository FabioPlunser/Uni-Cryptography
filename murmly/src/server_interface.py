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
log = logging.getLogger(__name__)


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

    def check_auth_publickey(self, username: str, key: paramiko.PKey):
        logging.info(
            f"Attempting public key auth for user '{username}' from {self.client_address}"
        )

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
        log.info(f"PTY requested: term={term}, size={width}x{height}")
        self.channel = channel # Store the channel when PTY is requested

        # --- Crucial Part ---
        # Try to find the driver and notify it of the initial size.
        # This is tricky because the driver might not exist yet.
        # The driver's start_application_mode now handles getting initial size
        # from the context, which gets it from the channel.
        # We might still need to handle *subsequent* resizes here.
        # For now, let the driver pull initial size. Subsequent resizes
        # need a mechanism (e.g., storing driver ref or using app).

        return True # Approve PTY request

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        log.info(f"Window change requested: size={width}x{height}")

        # --- Crucial Part ---
        # Find the driver instance associated with this channel/app and call process_resize
        # This requires linking the channel back to the correct driver instance.
        # Option 1: Store driver on the Server instance (if lifecycle allows)
        # Option 2: Look up driver via the app instance (if accessible)
        # Option 3: Pass resize info through a queue back to the client_handler thread

        # Simplified approach (assuming app/driver accessible somehow - NEEDS PROPER IMPLEMENTATION):
        try:
            # This is pseudocode - you need a way to get the driver instance
            # associated with this specific 'channel'. Maybe via the 'app' instance?
            # If the Textual app instance is stored somewhere accessible:
            # app_instance = find_app_for_channel(channel) # Needs implementation
            # if app_instance and hasattr(app_instance, "_driver"):
            #     driver = app_instance._driver
            #     if driver and hasattr(driver, 'process_resize'):
            #          driver.process_resize(width, height)
            #     else:
            #          log.warning("Could not find driver or process_resize method for window change.")
            # else:
            #     log.warning("Could not find app instance for window change.")

            # For now, let's assume the context on the driver gets updated if needed.
            # The driver itself should enqueue the Textual event.
            # We just need to ensure the context object is updated.
            # If the driver holds the context:
            # driver = find_driver_for_channel(channel) # Needs implementation
            # if driver and driver.context:
            #      driver.process_resize(width, height) # Let driver handle context update + event

            # Direct update to context IF context is stored/accessible here (less ideal):
            # context = find_context_for_channel(channel) # Needs implementation
            # if context:
            #     context.resize(width, height)
            #     # Still need to trigger Textual event via driver...

            # Simplest for now: Log it. The driver should handle subsequent resizes via events.
            pass

        except Exception as e:
            log.error(f"Error processing window change: {e}", exc_info=True)

        return True # Approve window change
    
    def check_channel_shell_request(self, channel):
        # User has asked for a shell, signal the main thread
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        # Example: Allow sftp if needed
        # if name == 'sftp':
        #     return True
        return False # Disallow subsystems by default