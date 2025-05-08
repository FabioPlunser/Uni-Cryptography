import requests
import websocket
import json
import threading
import time
from datetime import datetime
import base64

import crypto_utils


class ChatClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.auth_token = None
        self.token_type = None
        self.username = None
        self.ws = None
        
        # encryption related stuff
        self.priv_key = None
        self.pub_key  = None
        self.session_keys = {} 
        self.dh_parameters = None

        
    def register(self, username, password):
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
        return {"Authorization": f"{self.token_type} {self.auth_token}"}
        
    def get_online_users(self):
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
            
            if "type" in data and data["type"] == "delivery_status":
                status = "sent" if data["delivered"] else "not sent"
                print(f"Message to {data["recipient"]}: {status}")
                return
                
            if "error" in data: 
                print(f"Error: {data["error"]}")
                return
            
            # handle the message
            sender = data.get("sender")
            content = data.get("content")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            
            if sender not in self.session_keys: 
                print(f"establishing secure channel with {sender}...")
                if not self.establish_sec_channel(sender):
                    print(f"Could not establish secure channel with {sender}")
                    return
                
            try:
                encoded_bytes = base64.b64decode(content)
                
                #decrypüt
                decrypted_message = crypto_utils.decrypt(
                    self.session_keys[sender], 
                    encoded_bytes
                )
                print(f"\n[{timestamp}] {sender}: {decrypted_message}")
            except Exception as e:
                print(f"Error decrypting message from {sender}: {e}")
            
            
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
        if not self.ws:
            print("WebSocket not connected")
            return False
            

        if  recipient not in self.session_keys:
            print(f"Establishing secure channel with {recipient}...")
            if not self.establish_sec_channel(recipient):
                print(f"Could not establish secure channel with {recipient}")
                return False

        try:
            encrypted_content = crypto_utils.encrypt(self.session_keys[recipient], content)
            
            encrypted_b64 = base64.b64encode(encrypted_content).decode('ascii')
            
            # Send via WebSocket
            message = {
                "recipient": recipient,
                "content": encrypted_b64
            }
            self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"Error encrypting/sending message: {e}")
            return False
        
    def start(self, username, password):
        """inits everything necessary for client: dh parameters (fginite field for dh), 
        public key, websocket connection"""
        if not self.login(username, password):
            print(f"Could not log in as {username}, trying to register")
            if not self.register(username, password):
                print("Registration failed")
                return False
            if not self.login(username, password):
                print("Login after registration failed")
                return False
            
        # TODO: here key gen, after fetching parameters from server.
        dh_params_status =self.get_dh_parameters() 
        if not dh_params_status:
            print("Failed to get DH parameters")
            return False
        k_pair = crypto_utils.generate_pair(self.dh_parameters)
        self.priv_key = k_pair[0]
        self.pub_key  = k_pair[1]
        self.upload_public_key()               

        self.connect_websocket()
        return True
        
    def stop(self):
        try:
            if self.ws:
                self.ws.close()
                print("WebSocket connection closed")
        except Exception as e:
            print(f"Error closing WebSocket: {e}")
            
            
    # --------------------------
    #crypto stuff
    
    def upload_public_key(self): 
        if not self.auth_token: 
            print("Not authenticated")
            return False
        
        pub_key_serialized = crypto_utils.serialize_pub_key(self.pub_key)
        pub_key_serialized_str = pub_key_serialized.decode("utf-8")
        
        send_json = {
            "public_key": pub_key_serialized_str
        }
        
        response = requests.put(
            url=f"{self.server_url}/users/me/public_key",
            json=send_json,             #no need to conver to json, as fastapi does this autmatically (spring boot ptsd :/)
            headers=self.get_auth_header()
        )
        
        if response.status_code == 200:
            print("Public key uploaded successfully")
            return True
        else:
            print(f"Failed to upload public key: {response.text}")
            return False
        
    def get_public_key_user(self, peer_username: str):
        if not self.auth_token: 
            print("Not authenticated")
            return False
        
        response = requests.get(
            url=f"{self.server_url}/users/{peer_username}/public_key",
            headers=self.get_auth_header()
        )
        
        if response.status_code == 200:
            public_key_data = response.json()
            public_key_serialized = public_key_data["public_key"].encode("utf-8")
            public_key = crypto_utils.deserialize_pub_key(public_key_serialized)
            return public_key
        else:
            print(f"Failed to get public key: {response.text}")
            return None
        
    def establish_sec_channel(self, peer_username: str): 
        if not self.auth_token: 
            print("Not authenticated")
            return False
        
        if peer_username in self.session_keys:
            print(f"Session key with {peer_username} already exists")
            return True
        
        peer_pub_key = self.get_public_key_user(peer_username)
        if peer_pub_key is None:
            print(f"Failed to retrieve public key for {peer_username}")
            return False
        
        try:
            shared_key = crypto_utils.exchange_and_derive(self.priv_key, peer_pub_key)
            self.session_keys[peer_username] = shared_key
            print(f"Secure channel established with {peer_username}")
            return True
        except Exception as e:
            print(f"Error establishing secure channel: {e}")
            return False
    
    def get_dh_parameters(self):
        if not self.auth_token: 
            print("Not authenticated")
            return False
       e
        response = requests.get(url=f"{self.server_url}/dh_params")
        
        if response.status_code == 200:
            params_data = response.json()
            serialized_params = params_data["params"].encode("utf-8")
            self.dh_parameters = crypto_utils.deserialize_parameters(serialized_params)
            return True
        else:
            print(f"Failed to get DH parameters: {response.text}")
            return False


def chat_interface(client):
    """Simple chat interface, generated with lots of help by genAI"""
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