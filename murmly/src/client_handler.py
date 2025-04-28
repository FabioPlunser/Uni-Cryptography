import paramiko
import asyncio
import loggin
import threading


async def start_textual_app():
    """Starts the Textual app."""
    return True


async def handle_client(
    client_socket,
    client_address,
    db_conn,
    host_key,
    active_channels_dict,
    channels_lock,
    user_queues_dict,
    queues_lock,
):
    return True
