from textual.app import App, ComposeResult, RenderResult
from textual.widgets import (
    Header,
    Footer,
    Input,
    Log,
    Static,
    ListView,
    ListItem,
    Label,
)  # Added ListView etc.
from textual.containers import Vertical, Horizontal, Container
from textual.reactive import reactive
from textual.binding import Binding  # For custom bindings
from datetime import datetime

import asyncio


class ChatInterface(App):
    """Textual app for the Murmly chat interface."""

    CSS_PATH = "chat_interface.tcss"
    BINDINGS = [
        Binding("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        Binding("ctrl+l", "list_users", "List Online Users"),
        Binding("ctrl+c", "quit", "Quit Chat", show=True),  # Use Ctrl+C for quit
        # Add more bindings for chat commands if desired
    ]

    # --- Reactive variables to update UI elements ---
    current_recipient = reactive(None)

    def __init__(self, message_queue: asyncio.Queue, **kwargs):
        super().__init__(**kwargs)
        self._message_queue = message_queue  # Store the dedicated queue
        # Injected by server.py after __init__
        self.username = "Unknown"
        self.db_conn = None
        self.channel = None
        self.get_online_users_func = lambda: []
        self.send_message_func = None
        self.start_e2ee_func = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Vertical(id="chat-area"):
                yield Log(
                    id="chat-log", highlight=True, markup=True, auto_scroll=True
                )  # Enable auto_scroll
                yield Input(placeholder="Type a message or command (/help)", id="input")
            with Vertical(id="sidebar"):
                yield Static("Online Users:", id="online-users-header")
                yield ListView(id="online-users-list")
        yield Footer()
