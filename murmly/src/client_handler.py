import paramiko
import asyncio
import logging
import threading

from chat_app_interface import ChatInterface
from server_interface import Server


async def start_textual_app():
    """Starts the Textual app."""
    return True


def handle_client(
    client_socket,
    client_address,
    host_key,
    db,
    active_channels,
    active_channels_lock,
    user_message_queues,
    user_message_queues_lock,
):
    """Handles a single client connection."""
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

            # Add user to active channels
            with active_channels_lock:
                if username not in active_channels:
                    active_channels[username] = channel
                    logging.info(f"User '{username}' added to active channels.")
    except paramiko.SSHException as e:
        logging.error(f"SSH error: {e}")
    except Exception as e:
        logging.error(f"Error handling client {client_address}: {e}")

    return True
