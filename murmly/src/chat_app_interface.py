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


async def send_message_handler(recipient_id: int, message_content: str):
    """Handles sending a message to the recipient."""
