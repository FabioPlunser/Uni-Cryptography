# src/shared_state.py
import threading

user_message_queues = {}
user_message_queues_lock = threading.Lock()
active_channels = {}
active_channels_lock = threading.Lock()


# --- Helper Function ---
def get_active_users_safely() -> list[str]:
    """
    Safely retrieves a list of usernames from the active_channels dictionary.
    Acquires the lock to ensure thread safety during access.
    """
    with active_channels_lock:
        # Return a *copy* of the keys (usernames)
        # This prevents holding the lock while the app processes the list
        return list(active_channels.keys())
