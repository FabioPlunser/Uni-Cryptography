from fastapi import WebSocket

from db_utils import User


from logger import logger


class SocketManager:
    # inspiration from:
    # https://medium.com/@chodvadiyasaurabh/building-a-real-time-chat-application-with-fastapi-and-websocket-9965778e97be

    def __init__(
        self,
    ):
        self.connections = {}

    async def connect(self, websocket: WebSocket, user: User):
        await websocket.accept()
        self.connections[user.id] = websocket
        logger.info(f"User {user.username} connected with id: {user.id}")

    async def disconnect(self, user: User):
        websocket = self.connections.get(user.id)
        if websocket:
            await websocket.close()
            del self.connections[user.id]
            logger.info(f"User {user.username} disconnected with id: {user.id}")

    async def send_message(self, message: dict, user: User) -> bool:
        try:
            if user.id in self.connections:
                websocket = self.connections[user.id]
                logger.info(f"Sending message to {user.username}: {message}")
                await websocket.send_json(message)
                return True

            raise ValueError(
                f"User {user.username} with id: {user.id} is not connected."
            )
        except Exception as e:
            print(f"Error sending message to {user.username}: {e}")
            raise e
