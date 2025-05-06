from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from pydantic import BaseModel
import base64
from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext


import signal
import sys

def signal_handler(sig, frame):
    print("Shutting down server...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


from db_utils import User, Base

# Create FastAPI app
app = FastAPI(title="Murmly Chat API")

# Database setup (reusing elements from your existing code)
DATABASE_URL = "sqlite+aiosqlite:///murmly.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# JWT settings
SECRET_KEY = "your-secret-key-here"  # In production use a proper secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully!")

# Add a startup event handler
@app.on_event("startup")
async def startup_event():
    await init_db()
    print("Database initialized during startup!")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    public_key: Optional[str] = None

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    username: str

# Authentication helpers
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

# Database dependency
async def get_db():
    db = async_session_maker()
    try:
        yield db
    finally:
        await db.close()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Endpoints
@app.post("/register", response_model=UserBase)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    db_user = await get_user(user.username, db)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username,
        hashed_password=hashed_password,
        public_key_b64=user.public_key if user.public_key else None,
        is_online=True
    )
    
    db.add(new_user)
    await db.commit()
    
    return {"username": new_user.username}

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
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

# User dependency for protected routes
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
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


@app.get("/users/me", response_model=UserBase)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user