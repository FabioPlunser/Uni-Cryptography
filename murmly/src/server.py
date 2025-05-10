from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime, timedelta
from socket_manager import SocketManager
from db_utils import Database, User
from models import (
    UserBase,
    UserCreate,
    Token,
    TokenData,
    PublicKeyUpdate,
    PublicKeyResponse,
    Message,
    MessageSchema,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from config import PRIME_BITS, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

import crypto_utils
import jwt

# =============================================================================
from logger import logger

# =============================================================================
# database setup
DATABASE_URL = "sqlite+aiosqlite:///murmly.db"
db = Database(DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    print("Database initialized during startup!")
    yield


app = FastAPI(title="Murmly Chat API", lifespan=lifespan)

# Mount the SvelteKit build output
if os.path.exists("website/build"):
    app.mount("/", StaticFiles(directory="website/build", html=True), name="static")

# Add a catch-all route to serve index.html for client-side routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if os.path.exists("website/build"):
        return FileResponse("website/build/index.html")
    raise HTTPException(status_code=404, detail="Not found")

# Keep your existing CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

socket_manager = SocketManager()
dh_params = crypto_utils.generate_dh_parameters()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/register", response_model=UserBase)
async def register_user(user: UserCreate):
    """Register a new user and return access token"""
    logger.info(f"Registering user: {user}")
    db_user = await db.get_user_by_username(user.username)
    if db_user:
        logger.warning(f"Username already registered: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    try:
        user = await db.create_user(user.username, user.password)

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register user: {e}",
        )

    if not user:
        logger.error(f"Failed to create user: {user}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create user: {user}",
        )

    return {"success": True, "username": user.username}


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and return access token"""
    logger.info(
        f"Logging in user: {form_data.username}, password: {form_data.password}"
    )
    try:
        user = await db.get_user_by_username_and_password(
            form_data.username, form_data.password
        )
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Couldn't find user: {e}",
        )
    if not user:
        logger.warning(f"Invalid credentials for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    logger.info(f"User logged in successfully: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # TODO Refresh token if expired
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = await db.get_user_by_username(token_data.username)
    await db.set_user_online_status(user, True)
    if user is None:
        raise credentials_exception
    return user


@app.put("/update_public_key", response_model=dict)
async def update_public_key(
    public_key_update: PublicKeyUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update the public key of the current user"""
    logger.info(f"Updating public key for user: {current_user.username}")
    await db.update_user_public_key(current_user, public_key_update.public_key)
    return {"status": "success"}


@app.get("/users/{userId}/public_key", response_model=PublicKeyResponse)
async def get_user_public_key(
    userId: int,
    current_user=Depends(get_current_user),
):
    """Get the public key of a user"""
    logger.info(f"Retrieving public key for user: {userId}")
    user = await db.get_user_by_id(user_id=userId)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot retrieve own public key",
        )

    if not user.public_key_b64:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public key not found for user",
        )

    return {"username": user.username, "public_key": user.public_key_b64}


@app.get("/dh_params")
def get_dh_params():
    """Diffie hellman parameters for exchange"""
    if not dh_params:
        logger.error("DH params not available")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DH params not available",
        )

    serialized_params = crypto_utils.serialize_parameters(dh_params)
    serialized_params_str = serialized_params.decode("utf-8")
    logger.info(f"Serialized DH params: {serialized_params_str}")
    return {"params": serialized_params_str}


@app.get("/dh_params_js")
async def get_dh_params_for_js():
    """Diffie hellman parameters for exchange"""
    if not dh_params:
        logger.error("DH params not available")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DH params not available",
        )
    return crypto_utils.get_dh_params_as_hex(dh_params)


# inspiration for messaging app from:
# https://medium.com/@chodvadiyasaurabh/building-a-real-time-chat-application-with-fastapi-and-websocket-9965778e97be
@app.websocket("/ws/{token}")
async def websocket_endpoint(token: str, websocket: WebSocket):
    user = None

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_name = payload.get("sub")
    if user_name is None:
        await websocket.close()
        return

    user = await db.get_user_by_username(user_name)
    if not user:
        await websocket.close()
        return

    await db.set_user_online_status(user, True)
    await socket_manager.connect(websocket, user)

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect as e:
                print(f"WebSocket disconnected: {e}")
                break

            recipient = UserBase(**data.get("recipient"))
            logger.info(f"Recipient ID: {recipient.id}")
            content = data.get("content")
            message_number = data.get("message_number", 0)  # Get message number, default to 0

            logger.info(f"Getting recipient user by ID: {recipient.id}") 
            recipient_user = await db.get_user_by_id(recipient.id)
            logger.info(f"Recipient user: {recipient_user}")
            if not recipient_user:
                await websocket.send_json({"error": "Recipient not found"})
                continue

            # Create message in database with message number
            message = await db.create_message(user, recipient_user, content)
            logger.info(f"Message created: {message}")
            # Update or create chat records for both users
            await db.update_user_chat(user.id, recipient_user.id, message.id)
            await db.update_user_chat(recipient_user.id, user.id, message.id)

            message_json = {
                "sender": {"id": user.id, "username": user.username},
                "recipient": {
                    "id": recipient_user.id,
                    "username": recipient_user.username,
                },
                "content": content,
                "timestamp": message.timestamp.isoformat(),
                "message_number": message_number,  # Include message number in response
                "is_new_chat": True,
            }

            logger.info(f"Message JSON: {message_json}")
            logger.info(f"Sending message to {recipient_user.username}: {message_json}")

            message_sent = await socket_manager.send_message(
                message=message_json, user=recipient_user
            )
            logger.info(f"Message sent status: {message_sent}")

            if not message_sent:
                await websocket.send_json({"error": "Message not sent"})
                continue

    except Exception as e:
        print(f"WebSocket error: {e}")
        await socket_manager.disconnect(user)
        await websocket.close()
    finally:
        await db.set_user_online_status(user, False)


@app.get("/users/online")
async def get_online_users(current_user: User = Depends(get_current_user)):
    """Get all users that the current user has chatted with plus additional users"""
    # Get all users the current user has chatted with
    user_chats = await db.get_user_chats(current_user.id)
    chat_peer_ids = {chat.peer_id for chat in user_chats}
    
    # Get all users
    all_users = await db.get_all_users()
    
    # Format response with chat history info
    users_with_chat_info = []
    for user in all_users:
        if user.id == current_user.id:
            continue
            
        chat_info = next((chat for chat in user_chats if chat.peer_id == user.id), None)
        last_message = chat_info.last_message if chat_info else None
        
        users_with_chat_info.append({
            "id": user.id,
            "username": user.username,
            "is_online": user.is_online,
            "last_seen": user.last_seen.isoformat() if user.last_seen else None,
            "last_message": {
                "content": last_message.content if last_message else None,
                "timestamp": last_message.timestamp.isoformat() if last_message else None,
                "is_mine": last_message.sender_id == current_user.id if last_message else None
            } if last_message else None
        })
    
    return users_with_chat_info


@app.get("/users/{user_id}/chat")
async def get_chat_history(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get chat history between current user and specified user"""
    messages = await db.get_chat_history(current_user.id, user_id)
    return messages


@app.post("/users/ping")
async def ping_user(current_user: User = Depends(get_current_user)):
    """Update user's online status and last seen timestamp"""
    await db.update_user_status(current_user.id, True)
    return {"status": "ok"}


@app.get("/users/me", response_model=UserBase)
async def read_users_me(current_user=Depends(get_current_user)):
    return current_user


@app.get("/users/{username}/messages", response_model=list[MessageSchema])
async def get_messages(username: str, current_user=Depends(get_current_user)):
    """Get a list of messages for a user"""
    user = await db.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot retrieve own messages",
        )

    messages = await db.get_messages(user)
    return messages


@app.post("/logout", response_model=dict)
async def logout(current_user=Depends(get_current_user)):
    """Logout the user"""
    await db.set_user_online_status(current_user, False)

    return {"status": "success"}
