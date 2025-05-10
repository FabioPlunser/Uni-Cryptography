import requests
import websocket
import json
import threading
import time
from datetime import datetime, timezone
import base64
import os
import hashlib
import bcrypt


import crypto_utils
from config import *


class ChatClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.auth_token = None
        self.token_type = None
        self.username = None
        self.user_id = None
        self.ws = None

        # encryption related stuff
        self.priv_key = None
        self.pub_key = None
        self.session_keys = {}  # user_id -> KeyRotationManager
        self.message_counters = {}  # user_id -> message counter
        self.dh_parameters = None

    def hash_password(self, password):
        """Hash password using SHA-256 and convert to base64, matching website implementation"""
        # Create SHA-256 hash
        hash_obj = hashlib.sha256(password.encode())
        # Get bytes
        hash_bytes = hash_obj.digest()
        # Convert to base64
        return base64.b64encode(hash_bytes).decode('ascii')

    def register(self, username, password):
        hashed_password = self.hash_password(password)
        json_data = {
            "username": username,
            "password": hashed_password,
            "id": 0,  # This will be assigned by the server
            "is_online": False,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "has_chat": False
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
        hashed_password = self.hash_password(password)
        data = {
            "username": username, 
            "password": hashed_password
        }
        response = requests.post(f"{self.server_url}/token", data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.auth_token = token_data["access_token"]
            self.token_type = token_data["token_type"]
            self.username = username
            
            # Get user info to set user_id
            user_info = self.get_current_user()
            if user_info:
                self.user_id = user_info["id"]
                print(f"Logged in as {username} (ID: {self.user_id})")
                return True
            return False
        else:
            print(f"Login failed: {response.text}")
            return False

    def get_current_user(self):
        """Get current user information"""
        response = requests.get(
            f"{self.server_url}/users/me", headers=self.get_auth_header()
        )
        if response.status_code == 200:
            return response.json()
        return None

    def get_auth_header(self):
        return {"Authorization": f"{self.token_type} {self.auth_token}"}

    def get_online_users(self):
        response = requests.get(
            f"{self.server_url}/users/online", headers=self.get_auth_header()
        )
        if response.status_code == 200:
            users = response.json()
            return users
        else:
            print(f"Failed to get online users: {response.text}")
            return []

    def get_chat_history(self, peer_id):
        """Get chat history with a specific user"""
        response = requests.get(
            f"{self.server_url}/users/{peer_id}/chat", headers=self.get_auth_header()
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get chat history: {response.text}")
            return []

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)

            if "type" in data and data["type"] == "delivery_status":
                status = "sent" if data["delivered"] else "not sent"
                print(f"Message to {data['recipient']['username']}: {status}")
                return

            if "error" in data:
                print(f"Error: {data['error']}")
                return

            # handle the message
            sender = data.get("sender", {})
            sender_id = sender.get("id")
            sender_username = sender.get("username")
            content = data.get("content")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            message_number = data.get("message_number", 0)

            # check if secure channel / key exchange already happened
            if sender_id not in self.session_keys:
                print(f"establishing secure channel with {sender_username}...")
                if not self.establish_sec_channel(sender_id):
                    print(f"Could not establish secure channel with {sender_username}")
                    return

            try:
                encoded_bytes = base64.b64decode(content)

                # decrypt
                decrypted_message = self.decrypt_message(sender_id, encoded_bytes, message_number)

                # Check if this is a new chat
                is_new_chat = data.get("is_new_chat", False)
                if is_new_chat:
                    print(f"\n🔔 New chat from {sender_username}!")

                print(f"\n[{timestamp}] {sender_username}: {decrypted_message}")
            except Exception as e:
                print(f"Error decrypting message from {sender_username}: {e}")

        except Exception as e:
            print(f"Error processing message: {e}")
            print(f"Raw message: {message}")

    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")

    def on_open(self, ws):
        print("WebSocket connection established")

    def connect_websocket(self):
        """Connect to WebSocket endpoint"""
        # Convert http:// to ws:// or https:// to wss://
        ws_base_url = self.server_url.replace("http://", "ws://").replace(
            "https://", "wss://"
        )
        ws_url = f"{ws_base_url}/ws/{self.auth_token}"

        websocket.enableTrace(False)  # Set to True for debugging
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )

        # is a background thread
        def run_forever():
            self.ws.run_forever()

        thread = threading.Thread(target=run_forever, daemon=True)
        thread.start()
        time.sleep(1)  # sleep for letting connection establish

    def send_message(self, recipient_username, content):
        if not self.ws:
            print("WebSocket not connected")
            return False

        # Find recipient's user ID from online users
        online_users = self.get_online_users()
        recipient = next((user for user in online_users if user["username"] == recipient_username), None)
        
        if not recipient:
            print(f"User {recipient_username} not found or not online")
            return False

        recipient_id = recipient["id"]

        if recipient_id not in self.session_keys:
            print(f"Establishing secure channel with {recipient_username}...")
            if not self.establish_sec_channel(recipient_id):
                print(f"Could not establish secure channel with {recipient_username}")
                return False

        try:
            encrypted_content, message_number = self.encrypt_message(recipient_id, content)
            encrypted_b64 = base64.b64encode(encrypted_content).decode("ascii")

            message = {
                "recipient": {"id": recipient_id, "username": recipient_username},
                "content": encrypted_b64,
                "message_number": message_number
            }
            self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"Error encrypting/sending message: {e}")
            return False

    def start(self, username, password):
        """inits everything necessary for client: dh parameters (fginite field for dh),
        public key, websocket connection"""
        # Try login first
        if self.login(username, password):
            print("Login successful")
        else:
            print(f"Could not log in as {username}, trying to register")
            if not self.register(username, password):
                print("Registration failed")
                return False
            # Try login again after registration
            if not self.login(username, password):
                print("Login after registration failed")
                return False

        # TODO: here key gen, after fetching parameters from server.
        dh_params_status = self.get_dh_parameters()
        if not dh_params_status:
            print("Failed to get DH parameters")
            return False
        k_pair = crypto_utils.generate_pair(self.dh_parameters)
        self.priv_key = k_pair[0]
        self.pub_key = k_pair[1]
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
    # crypto stuff

    def upload_public_key(self):
        if not self.auth_token:
            print("Not authenticated")
            return False

        pub_key_serialized = crypto_utils.serialize_pub_key(self.pub_key)
        pub_key_serialized_str = pub_key_serialized.decode("utf-8")

        send_json = {"public_key": pub_key_serialized_str}

        response = requests.put(
            url=f"{self.server_url}/upload_public_key",
            json=send_json,  # no need to conver to json, as fastapi does this autmatically (spring boot ptsd :/)
            headers=self.get_auth_header(),
        )

        if response.status_code == 200:
            print("Public key uploaded successfully")
            return True
        else:
            print(f"Failed to upload public key: {response.text}")
            return False

    def get_public_key_user(self, peer_id):
        if not self.auth_token:
            print("Not authenticated")
            return False

        response = requests.get(
            url=f"{self.server_url}/users/{peer_id}/public_key",
            headers=self.get_auth_header(),
        )

        if response.status_code == 200:
            public_key_data = response.json()
            public_key_serialized = public_key_data["public_key"].encode("utf-8")
            try:
                public_key = crypto_utils.deserialize_pub_key(public_key_serialized, self.dh_parameters)
                return public_key
            except Exception as e:
                print(f"Error deserializing public key: {e}")
                return None
        else:
            print(f"Failed to get public key: {response.text}")
            return None

    def establish_sec_channel(self, peer_id):
        if not self.auth_token:
            print("Not authenticated")
            return False

        if peer_id in self.session_keys:
            print(f"Session key with peer {peer_id} already exists")
            return True

        peer_pub_key = self.get_public_key_user(peer_id)
        if peer_pub_key is None:
            print(f"Failed to retrieve public key for peer {peer_id}")
            return False

        try:
            shared_key = crypto_utils.exchange_and_derive(self.priv_key, peer_pub_key)
            # Initialize KeyRotationManager with the initial shared key
            self.session_keys[peer_id] = crypto_utils.KeyRotationManager(shared_key)
            self.message_counters[peer_id] = 0
            print(f"Secure channel established with peer {peer_id}")
            return True
        except Exception as e:
            print(f"Error establishing secure channel: {e}")
            return False

    def get_dh_parameters(self):
        if not self.auth_token:
            print("Not authenticated")
            return False
        response = requests.get(url=f"{self.server_url}/dh_params")

        if response.status_code == 200:
            params_data = response.json()
            serialized_params = params_data["params"].encode("utf-8")
            self.dh_parameters = crypto_utils.deserialize_parameters(serialized_params)
            return True
        else:
            print(f"Failed to get DH parameters: {response.text}")
            return False

    def encrypt_message(self, peer_id, message: str) -> tuple[bytes, int]:
        """
        Encrypt a message for a peer, handling key rotation.
        Returns the encrypted message and the message number.
        """
        if peer_id not in self.session_keys:
            if not self.establish_sec_channel(peer_id):
                raise Exception(f"No secure channel with peer {peer_id}")

        key_manager = self.session_keys[peer_id]
        message_number = self.message_counters[peer_id]
        
        # Get current key and encrypt
        current_key = key_manager.get_current_key()
        encrypted = crypto_utils.encrypt(current_key, message)
        
        # Increment counter and rotate key if needed
        key_manager.increment_counter()
        self.message_counters[peer_id] += 1
        
        return encrypted, message_number

    def decrypt_message(self, peer_id, encrypted_message: bytes, message_number: int) -> str:
        """
        Decrypt a message from a peer, handling key rotation.
        """
        if peer_id not in self.session_keys:
            if not self.establish_sec_channel(peer_id):
                raise Exception(f"No secure channel with peer {peer_id}")

        key_manager = self.session_keys[peer_id]
        
        # Get the key that was used for this message number
        key = key_manager.get_key_for_message(message_number)
        
        # Decrypt using the appropriate key
        decrypted = crypto_utils.decrypt(key, encrypted_message)
        return decrypted.decode('utf-8')


def chat_interface(client):
    """Simple chat interface with enhanced user information and chat history"""
    print("\n=== Chat Commands ===")
    print("/users - List online users with chat history")
    print("/history @username - Show chat history with a user")
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
                            status = "🟢" if user["is_online"] else "⚫"
                            last_seen = f" (Last seen: {user['last_seen']})" if user["last_seen"] else ""
                            print(f"{status} {user['username']}{last_seen}")
                            
                            # Show last message if available
                            if user.get("last_message"):
                                msg = user["last_message"]
                                is_mine = "You" if msg["is_mine"] else user["username"]
                                print(f"  Last message: {is_mine}: {msg['content']} ({msg['timestamp']})")
                            print()
                    else:
                        print("No other users online")

                elif command.startswith("history"):
                    parts = command.split()
                    if len(parts) != 2 or not parts[1].startswith("@"):
                        print("Usage: /history @username")
                        continue
                    
                    username = parts[1][1:]  # Remove @
                    users = client.get_online_users()
                    user = next((u for u in users if u["username"] == username), None)
                    
                    if not user:
                        print(f"User {username} not found")
                        continue
                    
                    history = client.get_chat_history(user["id"])
                    if history:
                        print(f"\nChat history with {username}:")
                        for msg in history:
                            sender = "You" if msg["sender_id"] == client.user_id else username
                            print(f"[{msg['timestamp']}] {sender}: {msg['content']}")
                    else:
                        print(f"No chat history with {username}")

                elif command == "quit":
                    break

                elif command == "help":
                    print("\n=== Chat Commands ===")
                    print("/users - List online users with chat history")
                    print("/history @username - Show chat history with a user")
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
    username = input("Enter username: ")
    password = input("Enter password: ")

    client = ChatClient(SERVER_URL)
    if client.start(username, password):
        chat_interface(client)
    else:
        print("Failed to start client")
