# custom_driver.py
import logging
import threading
import sys
import asyncio
from codecs import getincrementaldecoder
from typing import TYPE_CHECKING, Optional, Tuple

import paramiko
from rich.text import Text
from textual.driver import Driver

# MessageTarget is not directly used here, can be removed if not needed elsewhere
# from textual._types import MessageTarget
from textual._parser import ParseError  # Keep if you might catch it
from textual._xterm_parser import XTermParser
from textual.events import Resize
from textual.geometry import Size

if TYPE_CHECKING:
    from textual.app import App

log = logging.getLogger("textual.driver")


# Helper for encoding output (keep as is)
def encode_output(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding, "replace")


# --- Context Object (Revised __init__) ---
class ParamikoContext:
    """Holds the Paramiko channel and related state for the driver"""

    def __init__(
        self,
        channel: "paramiko.Channel",
        encoding: str = "utf-8",
        initial_width: int = 80,  # Added
        initial_height: int = 24,  # Added
    ):
        self.channel = channel
        self.encoding = encoding
        # Store initial size directly
        self.width: int = initial_width
        self.height: int = initial_height
        log.info(
            f"--- ParamikoContext: Initialized with size {self.width}x{self.height} ---"
        )
        # Removed unreliable _update_size() call from here

    @property
    def initial_size(self) -> Tuple[int, int]:
        """Returns the initial size of the terminal."""
        return self.width, self.height

    def resize(self, width: int, height: int) -> None:
        """Updates the context size (called by process_resize)."""
        self.width = width
        self.height = height
        log.info(f"--- ParamikoContext: Resized to {width}x{height} ---")


# --- Custom Driver (Revised Initialization Logic) ---
class NoSignalSshDriver(Driver):
    """
    Textual driver for Paramiko worker threads using direct channel I/O.
    Avoids termios/tty and signal handling.
    """

    def __init__(self, app: "App", **kwargs):
        # Pass debug=True from kwargs if you want parser debugging
        super().__init__(app, **kwargs)
        # app is stored as self._app by the base Driver class

        self._exit_event = threading.Event()
        self._input_thread: Optional[threading.Thread] = None
        self.context: Optional[ParamikoContext] = None  # Will be set via app.context
        self._parser: Optional[XTermParser] = None  # Initialized in start_app_mode
        self._decode = None  # Initialized in start_app_mode

        log.info("--- NoSignalSshDriver: Initializing ---")
        # DO NOT initialize context or parser here

    # Removed _initialize_context_and_parser method

    def write(self, data: str) -> None:
        """Writes directly to the Paramiko channel."""
        # Check context existence first
        if not self.context or not self.context.channel:
            log.warning("--- NoSignalSshDriver: Write ignored (no context/channel) ---")
            return

        if self._exit_event.is_set():
            # log.info(f"--- NoSignalSshDriver: Write ignored (exiting): {data!r} ---")
            return

        try:
            # Check channel activity *before* potentially blocking sendall
            if not self.context.channel.active:
                log.warning(
                    "--- NoSignalSshDriver: Write ignored, channel inactive ---"
                )
                if not self._exit_event.is_set():
                    self.stop()  # Trigger stop if channel died unexpectedly
                return

            encoded_data = encode_output(data, self.context.encoding)
            self.context.channel.sendall(encoded_data)
            # log.info(f"--- NoSignalSshDriver: Sent: {encoded_data!r} ---")

        except (
            paramiko.SSHException,
            EOFError,
            OSError,
            AttributeError,
            BrokenPipeError,
        ) as e:
            log.warning(
                f"--- NoSignalSshDriver: Error during channel send (connection closed?): {e} ---"
            )
            if not self._exit_event.is_set():
                self.stop()  # Trigger stop on send error
        except Exception as e:
            log.error(
                f"--- NoSignalSshDriver: Unexpected error during channel send: {e} ---",
                exc_info=True,
            )
            if not self._exit_event.is_set():
                self.stop()  # Trigger stop on unexpected error

    def _run_input_thread(self) -> None:
        """Input reading thread (target for threading.Thread)."""
        log.info("===> INPUT THREAD: Started.")

        # --- RESTORE INITIAL CHECKS ---
        if not self.context or not self.context.channel:
            log.error("===> INPUT THREAD: Exiting - context/channel missing.")
            self.stop()
            return
        if not self._parser or not self._decode:  # Assuming you need parser later
            log.error("===> INPUT THREAD: Exiting - parser/decoder missing.")
            self.stop()
            return
        if not hasattr(self, "_app") or self._app is None:
            log.error("===> INPUT THREAD: Exiting - app instance missing.")
            self.stop()
            return
        # --- END RESTORED CHECKS ---

        channel = self.context.channel
        exit_event = self._exit_event
        decode = self._decode
        parser = self._parser

        log.info(f"===> INPUT THREAD: Entering loop. Channel active: {channel.active}")

        try:
            while not exit_event.is_set():
                try:
                    # Check if channel is still active
                    if not channel.active:
                        log.warning(
                            "===> INPUT THREAD: Detected inactive channel in loop."
                        )
                        break

                    # *** USE recv_ready() TO AVOID BLOCKING ***
                    if channel.recv_ready():
                        log.info(
                            "===> INPUT THREAD: channel.recv_ready() is TRUE. Calling recv..."
                        )
                        try:
                            raw_data = channel.recv(65536)  # Read available data
                            log.info(f"===> INPUT THREAD: Received raw: {raw_data!r}")

                            if not raw_data:
                                log.info(
                                    "===> INPUT THREAD: Received EOF (empty data)."
                                )
                                break

                            # --- Process the data (Decode and Feed Parser) ---
                            try:
                                unicode_data = decode(raw_data)
                                log.info(
                                    f"===> INPUT THREAD: Decoded: {unicode_data!r}"
                                )
                                if unicode_data:
                                    log.info(
                                        "===> INPUT THREAD: Calling parser.feed..."
                                    )
                                    log.info(
                                        f"===> INPUT THREAD: Parser unicode_dat: {unicode_data}"
                                    )
                                    data = parser.feed(
                                        unicode_data
                                    )  # Feed the actual parser
                                    log.info(
                                        f"===> INPUT THREAD: Parser returned: {data}"
                                    )
                                    for item in data:
                                        log.info(
                                            f"===> INPUT THREAD: Parser item: {item}"
                                        )
                                        self._app.post_message(item)

                                    log.info("===> INPUT THREAD: parser.feed returned.")
                                else:
                                    log.info(
                                        "===> INPUT THREAD: Decoded data is empty."
                                    )
                            except Exception as decode_parse_error:
                                log.error(
                                    f"===> INPUT THREAD: Error decoding/parsing input: {decode_parse_error}",
                                    exc_info=True,
                                )
                            # --- End Process Data ---

                        except Exception as recv_err:
                            log.error(
                                f"===> INPUT THREAD: Error during channel.recv(): {recv_err}",
                                exc_info=True,
                            )
                            break  # Exit on recv error
                    else:
                        # No data ready, wait briefly using the exit event's wait
                        # This allows the loop to check exit_event periodically
                        if exit_event.wait(timeout=0.05):  # Wait up to 50ms
                            log.info(
                                "===> INPUT THREAD: Exit event detected during wait."
                            )
                            break  # Exit event was set

                except (
                    paramiko.SSHException,
                    EOFError,
                    OSError,
                    AttributeError,
                    BrokenPipeError,
                ) as e:
                    log.warning(f"===> INPUT THREAD: Channel error in loop: {e}")
                    break
                except Exception as e:
                    log.error(
                        f"===> INPUT THREAD: Unexpected error in loop: {e}",
                        exc_info=True,
                    )
                    break

        except Exception as e:
            log.error(
                f"===> INPUT THREAD: Unhandled error OUTSIDE loop: {e}", exc_info=True
            )
        finally:
            log.info("===> INPUT THREAD: Finished.")
            if not exit_event.is_set():
                self.stop()

    def start_application_mode(self) -> None:
        """Enter application mode. Initialize parser and input thread here."""
        log.info("--- NoSignalSshDriver: Entering application mode ---")

        # 1. Get Context (should be set on app instance before run_async)
        try:
            self.context = self._app.context
            if not isinstance(self.context, ParamikoContext):
                raise TypeError("app.context is not a ParamikoContext instance")
            log.info(
                f"--- NoSignalSshDriver: Context retrieved, size {self.context.initial_size} ---"
            )
        except AttributeError:
            log.error(
                "--- NoSignalSshDriver: FAILED to get context from app instance (app.context). "
                "Ensure app.context is set *before* calling app.run_async(). Stopping. ---"
            )
            self.stop()  # Signal exit
            raise RuntimeError("Driver context not found on App instance.")

        # 2. Initialize Decoder
        try:
            self._decode = getincrementaldecoder(self.context.encoding)().decode
            log.info(
                f"--- NoSignalSshDriver: Decoder initialized for {self.context.encoding} ---"
            )
        except Exception as e:
            log.error(
                f"--- NoSignalSshDriver: Failed to create decoder: {e}. Stopping. ---",
                exc_info=True,
            )
            self.stop()
            raise RuntimeError(
                f"Failed to create decoder for encoding {self.context.encoding}"
            )

        # 3. Initialize Parser (NO event queue check needed here)
        try:
            # Pass the debug flag from the driver's initialization
            debug = True
            self._parser = XTermParser(debug)
            log.info(
                f"--- NoSignalSshDriver: XTermParser initialized (debug={debug}) ---"
            )
        except Exception as e:
            log.error(
                f"--- NoSignalSshDriver: Failed to create XTermParser: {e}. Stopping. ---",
                exc_info=True,
            )
            self.stop()
            raise RuntimeError("Failed to create XTermParser")

        if self._input_thread is None:
            self._input_thread = threading.Thread(
                target=self._run_input_thread,
                name="textual-paramiko-input",
                daemon=True,  # Ensure thread exits if main process dies
            )
            self._input_thread.start()
        else:
            log.warning("--- NoSignalSshDriver: Input thread already exists? ---")

        # 5. Send Terminal Initialization Sequences
        write = self.write
        try:
            # Basic sequences (adjust based on target terminal compatibility)
            write("\x1b[?1049h")  # Enter alternate screen buffer
            write("\x1b[?25l")  # Hide cursor
            # write("\x1b[?1h")    # Set cursor key to application mode (optional)

            # Mouse support (SGR recommended if supported)
            # write("\x1b[?1006h")  # Enable SGR mouse reporting
            # write(
            #     "\x1b[?1003h"
            # )  # Enable mouse move reporting (any button down) - Often needed with SGR
            # write("\x1b[?1000h") # Enable mouse press/release reporting (X10) - Fallback if SGR fails

            # Enable bracketed paste mode (recommended)
            write("\x1b[?2004h")

            # Ensure initial screen clear and cursor position (optional but good practice)
            # write("\x1b[2J") # Clear screen
            # write("\x1b[H")  # Move cursor to home

            log.info("--- NoSignalSshDriver: Terminal init sequences sent ---")

        except Exception as e:
            log.error(
                f"--- NoSignalSshDriver: Error sending init sequences: {e}. Stopping. ---",
                exc_info=True,
            )
            self.stop()
            raise RuntimeError("Failed to send terminal init sequences")

        # 6. Set initial size via resize event
        # Context should have the correct initial size now
        initial_size = self.context.initial_size
        self.process_resize(initial_size[0], initial_size[1])

        log.info("--- NoSignalSshDriver: Application mode started ---")

    def stop_application_mode(self) -> None:
        """Exit application mode."""
        # This is called by Textual before stop()
        log.info("--- NoSignalSshDriver: Exiting application mode ---")

        # Set exit event first to signal threads/writes to stop
        self._exit_event.set()

        # Send deinitialization sequences (use write, check context/channel)
        if self.context and self.context.channel and self.context.channel.active:
            write = self.write
            write("\x1b[?1049h")  # Enter alternate screen buffer
            write("\x1b[?25l")  # Hide cursor
            # write("\x1b[?1006h") # COMMENT OUT MOUSE
            # write("\x1b[?1003h") # COMMENT OUT MOUSE
            # write("\x1b[?2004h") # COMMENT OUT PASTE
            log.info("--- NoSignalSshDriver: MINIMAL init sequences sent ---")

            # In stop_application_mode:
            write = self.write
            # write("\x1b[?2004l") # COMMENT OUT PASTE
            # write("\x1b[?1006l") # COMMENT OUT MOUSE
            # write("\x1b[?1003l") # COMMENT OUT MOUSE
            write("\x1b[?25h")  # Show cursor
            write("\x1b[?1049l")  # Exit alternate screen buffer
            log.info("--- NoSignalSshDriver: MINIMAL deinit sequences sent ---")
        else:
            log.warning(
                "--- NoSignalSshDriver: Skipping deinit sequences (no active channel/context) ---"
            )

        # Wait briefly for the input thread to exit
        if self._input_thread and self._input_thread.is_alive():
            log.info("--- NoSignalSshDriver: Waiting for input thread to join ---")
            self._input_thread.join(timeout=0.5)  # Wait max 0.5 seconds
            if self._input_thread.is_alive():
                log.warning(
                    "--- NoSignalSshDriver: Input thread did not exit cleanly ---"
                )
        self._input_thread = None  # Clear thread reference

        log.info("--- NoSignalSshDriver: Application mode stopped ---")

    def process_resize(self, width: int, height: int) -> None:
        """Processes a resize event (called internally or by ServerInterface)."""
        log.info(f"--- NoSignalSshDriver: Processing resize: {width}x{height} ---")

        # Update context immediately if available
        if self.context:
            self.context.resize(width, height)
        else:
            log.warning(
                "--- NoSignalSshDriver: process_resize called before context is ready ---"
            )
            return  # Cannot proceed without context

        # Enqueue a Textual Resize event using post_message for thread safety
        if hasattr(self, "_app") and self._app is not None:
            try:
                size = Size(width, height)
                # Sender is automatically added by post_message
                resize_event = Resize(size=size, virtual_size=size)
                self._app.post_message(resize_event)
                log.info(
                    f"--- NoSignalSshDriver: Enqueued resize event {size} via post_message ---"
                )
            except Exception as e:
                log.error(
                    f"--- NoSignalSshDriver: Failed to post_message resize event: {e} ---",
                    exc_info=True,
                )
        else:
            log.warning(
                "--- NoSignalSshDriver: App instance not available for resize event ---"
            )

    def stop(self) -> None:
        """Stop the driver cleanly (called by Textual)."""

        # *** ADD LOGGING HERE ***
        log.critical(
            f"##### DRIVER STOP() CALLED! Exit event was: {self._exit_event.is_set()} #####"
        )
        import traceback

        traceback.print_stack(
            file=sys.stderr
        )  # Print stack trace to see who called stop

        # This method is called by Textual during shutdown, usually after stop_application_mode
        if not self._exit_event.is_set():
            log.info(
                "--- NoSignalSshDriver: stop() called, ensuring exit event is set ---"
            )
            self._exit_event.set()
            # stop_application_mode should handle cleanup, but ensure thread join is attempted if needed
            if self._input_thread and self._input_thread.is_alive():
                self._input_thread.join(timeout=0.1)  # Short extra wait
            # Call super().stop() to ensure base class cleanup runs
            try:  # Add try/except just in case super().stop() fails
                super().stop()
            except Exception as e:
                log.error(f"--- NoSignalSshDriver: Error calling super().stop(): {e}")
            log.info("--- NoSignalSshDriver: stop() finished ---")

    def get_terminal_size(self) -> Tuple[int, int]:
        """Returns the current terminal size known by the context."""
        if self.context:
            return (self.context.width, self.context.height)
        else:
            # This might be called early by Textual before context is ready.
            log.warning(
                "--- NoSignalSshDriver: get_terminal_size called before context is initialized, returning default ---"
            )
            # Return a sensible default, Textual will get a Resize event later.
            return (80, 24)

    def disable_input(self) -> None:
        """Disable input (called by Textual)."""
        # Input is primarily managed by the input thread checking _exit_event.
        # Setting the event is the main way to stop input processing.
        log.info(
            "--- NoSignalSshDriver: disable_input called (action delegated to stop/exit_event) ---"
        )
        if not self._exit_event.is_set():
            # If called explicitly before a full stop, ensure the event is set.
            self._exit_event.set()
        # Call super().disable_input() in case the base class does something
        super().disable_input()

    # Ensure flush method exists if required by base class (Paramiko handles buffering)
    def flush(self) -> None:
        """Flush output buffer (no-op for Paramiko sendall/send)."""
        pass
