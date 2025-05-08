# chat_app_interface.py
import logging
import json

import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, RichLog, Label, ListView, ListItem
from textual.reactive import var
from textual import events

# from client_handler import get_active_users_safely, active_channels_lock, active_channels, encode_output # Adjust import as needed

from shared_state import (
    active_channels,
    active_channels_lock,
    user_message_queues,
    user_message_queues_lock,
    get_active_users_safely,
)

from .user_status_list_item import UserStatusListItem


log = logging.getLogger(__name__)


class ChatInterface(App):
    """Textual app for the Murmly chat interface."""

    CSS_PATH = "./css/chat_interface.tcss"
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("f1", "focus_search", "Focus User Search"),
        ("f2", "focus_message", "Focus Message Input"),
        ("f3", "focus_users", "Focus User List"),
        ("Tab", "", "Switch Focus"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_history: dict[str, list[str]] = {}
        self.session_keys: dict[str, bytes] = {}
        self.pending_dh_exchanges: dict[str, object] = {}
        self._active_list_users = set()
        self.title = "Murmly Chat"

    selected_user = var(None)
    username = var(None)
    chat_history = {}
    pending_dh_exchanges = {}

    def compose(self) -> ComposeResult:
        with Container(id="root-container"):
            with Container(id="app-frame"):
                with Horizontal(id="main-container"):
                    yield Header()
                    with VerticalScroll(id="sidebar"):
                        yield Label(f"Me: {self.username}", id="username")
                        yield Label("Online Users:", id="user-list-header")
                        yield Input(id="user-search", placeholder="Search Users")
                        yield ListView(id="user-list")

                    with Container(id="chat-container"):
                        yield RichLog(
                            id="chat-log", wrap=True, highlight=True, markup=True
                        )
                        yield Input(id="chat-input", placeholder="Message")
                    yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_focus_search(self) -> None:
        # self.query_one("#user-search").focus() # If search input exists
        pass

    def action_focus_message(self) -> None:
        self.query_one("#chat-input").focus()

    def action_focus_users(self) -> None:
        self.query_one("#user-list").focus()

    def on_key(self, event: events.Key):
        self.query_one(RichLog).write(event)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        log.info(f"===> APP: Input submitted: {event}")
        if event.input.id == "chat-input" and event.value:
            self.query_one("#chat-input").clear()

    def on_mount(self) -> None:
        log.info("===> APP: Mounting ChatInterface...")
        # Ensure username is set before proceeding
        if not self.username:
            log.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            log.error("!!! APP ERROR: self.username not set before mount!")
            log.error(
                "!!! Ensure username is passed during init or set before run_async."
            )
            log.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # self.exit("Username not configured") # Optionally exit
            # return

        self.set_interval(5.0, self.refresh_users)  # Check every 5 seconds
        self.refresh_users()  # Initial refresh
        self.query_one("#root-container").focus()
        log.info("===> APP: Mount complete.")

    def refresh_users(self) -> None:
        """Safely fetch users and trigger UI update via background worker."""
        # Avoid running if username isn't set yet
        if not self.username:
            log.warning("===> APP: Skipping user refresh, username not set.")
            return

        log.debug("===> APP: Refreshing user list...")
        # Use run_worker for background tasks to avoid blocking the UI thread
        self.run_worker(self._fetch_and_update_users, thread=True, group="user_refresh")

    async def _fetch_and_update_users(self) -> None:
        """Worker function to get users and schedule UI update."""
        try:
            users = get_active_users_safely()
            users_filtered = [u for u in users if u != self.username]
            log.debug(f"===> APP (Worker): Fetched users: {users_filtered}")
            self.call_from_thread(self.update_user_list, users_filtered)
        except Exception as e:
            log.error(f"===> APP (Worker): Failed to fetch users: {e}", exc_info=True)

    async def update_user_list(self, users_active_channel: list[str]):
        """Update the ListView widget with online users (add new, remove old)."""
        log.info(f"===> APP: Updating user list UI with: {users_active_channel}")
        try:
            user_list_view = self.query_one("#user-list", ListView)
            new_user_set = set(users_active_channel)

            current_users = self._active_list_users - new_user_set
            for username in current_users:
                try:
                    user = user_list_view.get_child_by_id(f"user-{username}")
                    log.info(user.classes)
                    if user:
                        log.info(f"===> APP: Update user: {username}")
                        user.username = username.capitalize()
                        user.update_status(True)
                except Exception as remove_err:
                    log.error(
                        f"Error removing user item {username}: {remove_err}",
                        exc_info=True,
                    )

            users_to_add = new_user_set - self._active_list_users
            for username in sorted(list(users_to_add)):
                if username not in self._active_list_users:
                    log.info(f"===> APP: Adding new online user: {username}")
                    item = UserStatusListItem(f"user-{username}", username.capitalize(), True)
                    item.username = username.capitalize()
                    item.update_status(True)
                    user_list_view.append(item)
                    self._active_list_users.add(username)

            if self.selected_user and self.selected_user not in new_user_set:
                log.info(
                    f"===> APP: Selected user {self.selected_user} went offline. Clearing selection."
                )
                self.selected_user = None
                self.query_one("#chat-log").clear()
                self.query_one("#chat-log").write(
                    "[System] Selected user went offline."
                )
                self.query_one("#chat-input").placeholder = (
                    "Select user & type message..."
                )
                user_list_view.index = None

        except Exception as e:
            log.error(f"===> APP: Failed to update user list UI: {e}", exc_info=True)
