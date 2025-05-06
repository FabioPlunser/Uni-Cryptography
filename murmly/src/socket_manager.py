from fastapi import WebSocket

from db_utils import User


class SocketManager:
    # inspiration from:
    # https://medium.com/@chodvadiyasaurabh/building-a-real-time-chat-application-with-fastapi-and-websocket-9965778e97be
   
    def __init__(self, ): 
        self.connections = {}
        
    async def connect(self, websocket: WebSocket, user: User):
        await websocket.accept()
        self.connections[user.id] = websocket
        print(f"User {user.username} with id: {user.id} connected.")
    
    async def disconnect(self, user: User):
        websocket = self.connections.get(user.id)
        if websocket:
            await websocket.close()
            del self.connections[user.id]
            print(f"User {user.username} with id: {user.id} disconnected.")
            
    async def send_message(self, message: dict, user: User) -> bool:
        if user.id in self.connections:
            websocket = self.connections[user.id]
            await websocket.send_json(message)
            return True

        return False
    
    