from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select

from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext


from db_utils import User, Base
from socket_manager import SocketManager
from models import *
from config import *
import crypto_utils

app = FastAPI(title="Murmly Chat API")

# managing all the connections for messaging
socket_manager = SocketManager()
dh_params = crypto_utils.generate_dh_parameters()   # parameters (g, p for galois field) are computed by server. 

# database setup
DATABASE_URL = "sqlite+aiosqlite:///murmly.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")


@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Database initialized during startup!")


#----------------------------
# authentication and authorization
# password hashing using cryptoContext: library from passlib, hope this is 
# ok as this is not in dependence of the dh implementation of e2ee
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user(username: str, db: AsyncSession):
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalars().first()


async def authenticate_user(username: str, password: str, db: AsyncSession):
    user = await get_user(username, db)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#----------------------------

async def get_db():
    db = async_session_maker()
    try:
        yield db
    finally:
        await db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/register", response_model=UserBase)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    db_user = await get_user(user.username, db)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        hashed_password=hashed_password,
        public_key_b64=None,
        is_online=True
    )

    db.add(new_user)
    await db.commit()

    return {"username": new_user.username}


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update online status
    user.is_online = True
    await db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception

    user = await get_user(token_data.username, db)
    if user is None:
        raise credentials_exception
    return user


@app.put("/users/me/public_key", response_model=dict)
async def update_public_key(
    public_key_update: PublicKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.public_key_b64 = public_key_update.public_key
    await db.commit()
    return {"status": "success"}


@app.get("/users/{username}/public_key", response_model=PublicKeyResponse)
async def get_user_public_key(
    username: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user(username, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot retrieve own public key",
        )
    # TODO: what happens if there is no pub key?

    return {"username": user.username, "public_key": user.public_key_b64}


@app.get("/dh_params")
def get_dh_params():
    """diffie hellman parameters for exchange"""
    if not dh_params:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DH params not available",
        )

    serialized_params = crypto_utils.serialize_parameters(dh_params)
    serialized_params_str = serialized_params.decode("utf-8")
    return {"params": serialized_params_str}


# inspiration for messaging app from:
# https://medium.com/@chodvadiyasaurabh/building-a-real-time-chat-application-with-fastapi-and-websocket-9965778e97be
@app.websocket("/ws/{token}")
async def websocket_endpoint(
    token: str, websocket: WebSocket, db: AsyncSession = Depends(get_db)
):
    user = None

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_name = payload.get("sub")
    if user_name is None:
        await websocket.close()
        return

    user = await get_user(user_name, db)
    if not user:
        await websocket.close()
        return

    await socket_manager.connect(websocket, user)

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect as e:
                print(f"WebSocket disconnected: {e}")
                break

            recipient_username = data.get("recipient")
            content = data.get("content")

            sender_username = user.username

            recipient_user = await get_user(recipient_username, db)
            if not recipient_user:
                await websocket.send_json({"error": "Recipient not found"})
                continue

            message_json = {
                "sender": sender_username,
                "recipient": recipient_username,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }

            message_sent = await socket_manager.send_message(
                message=message_json, user=recipient_user
            )

            await websocket.send_json(
                {
                    "type": "delivery_status",
                    "recipient": recipient_username,
                    "delivered": message_sent,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        print(f"WebSocket error: {e}")
        if user:
            await socket_manager.disconnect(user)
            user.is_online = False
            await db.commit()

        await websocket.close()


@app.get("/users/online", response_model=list[str])
async def get_online_users(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.is_online == True)
    result = await db.execute(stmt)
    online_users = result.scalars().all()

    online_users = [
        user.username for user in online_users if user.username != current_user.username
    ]
    return online_users


# test rest for auth - user only
@app.get("/users/me", response_model=UserBase)
async def read_users_me(current_user=Depends(get_current_user)):
    return current_user
