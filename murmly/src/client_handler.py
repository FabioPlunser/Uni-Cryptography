import paramiko
import asyncio
import logging

from server_interface import Server
from chat_app_interface import ChatInterface
from custom_driver import NoSignalSshDriver, ParamikoContext
from shared_state import (
    active_channels,
    active_channels_lock,
    user_message_queues,
    user_message_queues_lock,
)

log = logging.getLogger(__name__)


async def run_textual_app_asnync(channel, username, context: ParamikoContext):
    """
    Initializes and runs the Textual ChatInterface using the NoSignalLinuxDriver,
    explicitly passed during instantiation.
    """
    log.info(f"[{username}] --- run_textual_app_asnync: ENTER ---")
    chat_app_instance = None

    try:
        log.info(f"[{username}] Creating ParamikoContext...")

        log.info(
            f"[{username}] ParamikoContext created. Initial size: {context.initial_size}"
        )

        log.info(
            f"[{username}] Instantiating ChatInterface with driver_class=NoSignalLinuxDriver..."
        )

        chat_app_instance = ChatInterface(driver_class=NoSignalSshDriver)
        chat_app_instance.context = context
        chat_app_instance.username = username

        log.info(
            f"[{username}] ===> run_textual_app_asnync: Starting app.run_async()..."
        )
        await chat_app_instance.run_async()
        log.info(
            f"[{username}] ===> run_textual_app_asnync: app.run_async() COMPLETED."
        )

    except Exception as e:
        log.error(
            f"[{username}] ===> run_textual_app_asnync: EXCEPTION during execution: {e}",
            exc_info=True,
        )
    finally:
        log.info(f"[{username}] ===> run_textual_app_asnync: FINALLY block executing.")


def handle_client(
    client_socket,
    client_address,
    host_key,
    db,
):
    """Handles a single client connection."""
    username = None
    channel = None
    try:
        server_instance = Server(client_address, db)

        if not server_instance:
            return False

        logging.info(f"Waiting for auth from {client_address}...")

        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)
        transport.local_version = "SSH-2.0-MurmlyChatServer1.0"  # Optional Identifier
        transport.start_server(server=server_instance)

        logging.info(f"Waiting for auth from {server_instance.client_address}...")

        auth_event_happened = server_instance.event.wait(10)

        if auth_event_happened and server_instance.username and server_instance.channel:
            username = server_instance.username
            channel = server_instance.channel
            logging.info(f"User '{username}' authenticated successfully.")

            try:
                context = ParamikoContext(
                    channel=channel,
                    encoding="utf-8",
                )
                log.info(
                    f"[{username}] ParamikoContext created. Initial size: {context.initial_size}"
                )
            except Exception as context_e:
                log.error(f"[{username}] Failed to create ParamikoContext: {context_e}")
            # Add user to active channels
            with active_channels_lock:
                active_channels[username] = channel
                logging.info(f"User '{username}' added to active channels.")

            asyncio.run(run_textual_app_asnync(channel, username, context))

    except paramiko.SSHException as e:
        logging.error(f"SSH error: {e}")
    except Exception as e:
        logging.error(f"Error handling client {client_address}: {e}")
    finally:
        try:
            if username:
                # Remove user from active channels
                with active_channels_lock:
                    if username in active_channels:
                        del active_channels[username]
                        logging.info(f"User '{username}' removed from active channels.")
                    else:
                        logging.warning(
                            f"User '{username}' not found in active channels."
                        )

                    # Mark user as offline
                    asyncio.run(db.set_user_online_status(username, False))
                    logging.info(f"User '{username}' marked as offline.")

            if channel:
                try:
                    channel.close()
                    logging.info(f"Channel closed for user '{username}'.")
                except Exception as e:
                    logging.error(f"Error closing channel for user '{username}': {e}")

            if transport:
                try:
                    transport.close()
                    logging.info(f"Transport closed for user '{username}'.")
                except Exception as e:
                    logging.error(f"Error closing transport for user '{username}': {e}")

        except Exception as e:
            logging.error(f"Error removing user '{username}' from active channels: {e}")

    return True


