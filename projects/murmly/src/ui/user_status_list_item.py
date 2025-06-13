# src/user_status_list_item.py

import logging
from textual.app import ComposeResult

# Use Vertical for the two lines of text if desired
from textual.containers import Horizontal, Container, Vertical
from textual.reactive import var
from textual.widgets import Label, ListItem
from textual.message import Message  
from textual.css.query import NoMatches 

log = logging.getLogger(__name__)


class UserStatusListItem(ListItem):
    """A ListItem widget that displays a username and an online status dot."""
    COMPONENT_CLASSES = {
        "status-dot",
        "username-label",
    }
    is_online: var[bool] = var(False)
    def __init__(self, id: str, username: str, is_online: bool = False, **kwargs) -> None:
        super().__init__(id=id, **kwargs)
        self.username_text = username
        self.is_online = is_online
        self.user_data = username

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container():
            with Horizontal():
                yield Label("●", classes="status-dot")
                yield Label(self.username_text, classes="username-label")
            # Optional: Add last text label
            # yield Label(self.last_text, classes="last-text-label")

    def watch_is_online(self, online: bool) -> None:
        """Update the CSS class of the status dot when is_online changes."""
        # This watcher might run before compose finishes during init.
        # Check if the widget is mounted and query safely.
        if not self.is_mounted:
            # If not mounted, the query will fail. Defer the update.
            # The classes will be set correctly when compose runs based on the current self.is_online value.
            log.debug(f"Watcher skipped for {self.username_text} (not mounted yet)")
            return

        log.debug(f"Watcher: Updating status for {self.username_text}: {online}")
        try:
            # Query for the dot. If it doesn't exist yet, NoMatches is raised.
            dot = self.query_one(".status-dot", Label)
            dot.set_class(online, "online")
            dot.set_class(not online, "offline")
            log.debug(f"Dot classes for {self.username_text} after set_class: {dot.classes}")
        except NoMatches:
            # This can happen if the watcher runs before compose is fully done.
            # It's usually safe to ignore, as compose will set the initial state.
            log.warning(f"Watcher: Could not find '.status-dot' for {self.username_text} (likely timing issue).")
        except Exception as e:
            log.error(f"Error in watch_is_online for {self.username_text}: {e}", exc_info=True)

    def update_status(self, is_online: bool) -> None:
        """Public method to update the online status.
        Assigning to the reactive var triggers the watcher.
        """
        self.is_online = is_online