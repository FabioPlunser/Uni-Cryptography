import requests
import websocket
import json
import threading
import time
from datetime import datetime

class ChatClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.auth_token = None
        self.token_type = None
        self.username = None
        self.ws = None
        
    def register(self, username, password):
        """Register a new user"""
        json_data = {
            "username": username,
            "password": password,
        }
        response = requests.post(f"{self.server_url}/register", json=json_data)
        if response.status_code == 200:
            self.username = username
            print(f"Registered as {username}")
            return True
        else:
            print(f"Registration failed: {response.text}")
            return False
            
    def login(self, username, password):
        """Login and get auth token"""
        data = {
            "username": username,
            "password": password
        }
        response = requests.post(f"{self.server_url}/token", data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.auth_token = token_data["access_token"]
            self.token_type = token_data["token_type"]
            self.username = username
            print(f"Logged in as {username}")
            return True
        else:
            print(f"Login failed: {response.text}")
            return False
            
    def get_auth_header(self):
        """Get authorization header for authenticated requests"""
        return {"Authorization": f"{self.token_type} {self.auth_token}"}
        
    def get_online_users(self):
        """Get a list of online users"""
        response = requests.get(
            f"{self.server_url}/users/online",
            headers=self.get_auth_header()
        )
        if response.status_code == 200:
            users = response.json()
            return users
        else:
            print(f"Failed to get online users: {response.text}")
            return []
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            if 'type' in data and data['type'] == 'delivery_status':
                status = "sent" if data['delivered'] else "not sent"
                print(f"Message to {data['recipient']}: {status}")
                return
                
            # Handle incoming chat message
            sender = data.get("sender")
            content = data.get("content")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            
            print(f"\n[{timestamp}] {sender}: {content}")
        except Exception as e:
            print(f"Error processing message: {e}")
            print(f"Raw message: {message}")
        
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        print("WebSocket connection closed")
        
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        print("WebSocket connection established")
        
    def connect_websocket(self):
        """Connect to WebSocket endpoint"""
        # Convert http:// to ws:// or https:// to wss://
        ws_base_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_base_url}/ws/{self.auth_token}"
        
        # Create WebSocket connection
        websocket.enableTrace(False)  # Set to True for debugging
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        # is a background thread
        def run_forever():
            self.ws.run_forever()
            
        thread = threading.Thread(target=run_forever, daemon=True)
        thread.start()
        time.sleep(1)  # Give time for the connection to establish
        
    def send_message(self, recipient, content):
        """Send a message to a recipient"""
        if not self.ws:
            print("WebSocket not connected")
            return False
            
        # Send message via WebSocket
        message = {
            "recipient": recipient,
            "content": content
        }
        self.ws.send(json.dumps(message))
        return True
        
    def start(self, username, password):
        """Initialize the client and connect"""
        if not self.login(username, password):
            print(f"Could not log in as {username}, trying to register")
            if not self.register(username, password):
                print("Registration failed")
                return False
            if not self.login(username, password):
                print("Login after registration failed")
                return False
                
        # Connect to WebSocket
        self.connect_websocket()
        return True
        
    def stop(self):
        """Close the connection"""
        if self.ws:
            self.ws.close()

def chat_interface(client):
    """Simple chat interface"""
    print("\n=== Chat Commands ===")
    print("/users - List online users")
    print("/quit - Exit the chat")
    print("/help - Show commands")
    print("To send a message: @username Your message here")
    print("=====================\n")
    
    try:
        while True:
            user_input = input("> ")
            
            if user_input.startswith("/"):
                command = user_input[1:].lower()
                
                if command == "users":
                    users = client.get_online_users()
                    if users:
                        print("\nOnline users:")
                        for user in users:
                            print(f"- {user}")
                    else:
                        print("No other users online")
                        
                elif command == "quit":
                    break
                    
                elif command == "help":
                    print("\n=== Chat Commands ===")
                    print("/users - List online users")
                    print("/quit - Exit the chat")
                    print("/help - Show commands")
                    print("To send a message: @username Your message here")
                    print("=====================\n")
                    
                else:
                    print("Unknown command. Type /help for commands.")
                    
            elif user_input.startswith("@"):
                # Extract recipient and message
                parts = user_input[1:].split(" ", 1)
                if len(parts) < 2:
                    print("Usage: @username Your message here")
                    continue
                    
                recipient = parts[0]
                message = parts[1]
                
                # Send the message
                client.send_message(recipient, message)
                
            else:
                print("Invalid format. Use @username message or type /help")
                
    except KeyboardInterrupt:
        print("\nExiting chat...")
    finally:
        client.stop()

if __name__ == "__main__":
    SERVER_URL = "http://localhost:8000"
    
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    client = ChatClient(SERVER_URL)
    if client.start(username, password):
        chat_interface(client)
    else:
        print("Failed to start client")