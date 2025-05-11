from datetime import datetime
from typing import List, Optional
from passlib.context import CryptContext

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
    update,
    or_,
    and_,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, selectinload
from models import Base, User, Message, UserChat


# --- logger Setup ---
from logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    logger.debug(f"Verifying password: {plain_password}")
    logger.debug(f"Hashed password: {hashed_password}")
    return pwd_context.verify(plain_password, hashed_password)

# --- Database Interaction Class ---
class Database:
    def __init__(self, db_url="sqlite+aiosqlite:///murmly.db"):
        # echo=False is usually preferred for production/less verbose logs
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info(f"Async database engine created for {db_url}")

    async def init_db(self):
        """Initializes the database and creates tables if they don't exist."""
        async with self.engine.begin() as conn:
            logger.info("Running metadata create_all...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created.")
            logger.info("Database tables ensured.")

    # --- User Operations ---
    async def create_user(
        self,
        username: str,
        password: str,
    ) -> Optional[User]:
        """Creates a new user,"""
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt_exists = select(User).where((User.username == username))
                existing_user_res = await session.execute(stmt_exists)
                if existing_user_res.scalars().first():
                    logger.warning(
                        f"User '{username}' or their public key already exists."
                    )
                    raise ValueError(
                        f"User '{username}' already exists. Please choose a different username."
                    )

                hashed_password = get_password_hash(password)
                new_user = User(
                    username=username, password_hash=hashed_password, is_online=False
                )
                session.add(new_user)
                await session.flush()
                logger.info(f"Attempting to commit new user '{username}'")
            logger.info(f"Successfully created user '{username}' with id {new_user.id}")
            return new_user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        async with self.async_session_factory() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            user = result.scalars().first()
            return user

    async def get_user_by_username_and_password(
        self, username: str, password: str
    ) -> Optional[User]:
        """Authenticates a user by checking their username and password."""
        async with self.async_session_factory() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            user = result.scalars().first()
            if user and verify_password(password, user.password_hash):
                return user
            return None

    async def update_user_jwt(self, username: str, jwt: str) -> bool:
        """Updates the JWT for a user."""
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt = (
                    update(User)
                    .where(User.username == username)
                    .values(jwt=jwt)
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    logger.warning(
                        f"Attempted to update JWT for non-existent user '{username}'"
                    )
                    return False
                else:
                    logger.debug(f"Set user '{username}' JWT to {jwt}")
                    return True

    async def update_user_public_key(self, user: User, public_key_b64: str) -> bool:
        """Updates the public key for a user."""
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt = (
                    update(User)
                    .where(User.id == user.id)
                    .values(public_key_b64=public_key_b64)
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    logger.warning(
                        f"Attempted to update public key for non-existent user '{user.username}'"
                    )
                    return False
                else:
                    logger.debug(
                        f"Set user '{user.username}' public key to {public_key_b64}"
                    )
                    return True

    async def get_user_by_public_key(self, public_key_b64: str) -> Optional[User]:
        """Retrieves a user by their public key."""
        async with self.async_session_factory() as session:
            stmt = select(User).where(User.public_key_b64 == public_key_b64)
            result = await session.execute(stmt)
            user = result.scalars().first()
            return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        async with self.async_session_factory() as session:
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalars().first()
            return user

    async def get_online_users(self) -> List[User]:
        """Retrieves a list of usernames for all online users."""
        async with self.async_session_factory() as session:
            stmt = select(User).where(User.is_online == True)
            result = await session.execute(stmt)
            online_users = result.scalars().all()
            logger.info(f"Online users: {[user for user in online_users]}")
            return online_users

    async def set_user_online_status(self, user: User, is_online: bool) -> bool:
        """Updates the online status and last_seen for a user."""
        logger.info(f"Setting online status for user {user.username} to {is_online}")
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt = (
                    update(User)
                    .where(User.id == user.id)
                    .values(is_online=is_online, last_seen=datetime.utcnow())
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    logger.warning(
                        f"Attempted to update online status for non-existent user '{user.username}'"
                    )
                    return False
                else:
                    logger.debug(
                        f"Set user '{user.username}' online status to {is_online}"
                    )
                    return True

    async def create_message(
        self,
        sender_username: User,
        recipient_username: User,
        content: str,
        message_number: int = 0,
    ) -> Optional[Message]:
        """Stores an encrypted message, looking up user IDs first."""
        async with self.async_session_factory() as session:
            async with session.begin():
                message = Message(
                    sender_id=sender_username.id,
                    recipient_id=recipient_username.id,
                    content=content,
                    message_number=message_number,
                )
                session.add(message)
                await session.flush()
            logger.info(
                f"Stored message from {sender_username.username} to {recipient_username.username}"
            )
            return message

    async def get_messages(self, username: str) -> List[Message]:
        """Retrieves all messages for a user."""
        async with self.async_session_factory() as session:
            stmt = select(Message).where(Message.sender_id == username)
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return messages

    async def get_previous_messages(
        self, sender_username: User, recipient_username: User
    ) -> List[Message]:
        """Retrieves all messages between two users."""
        async with self.async_session_factory() as session:
            stmt = select(Message).where(
                (Message.sender_id == sender_username.id)
                & (Message.recipient_id == recipient_username.id)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return messages

    async def get_user_chats(self, user_id: int) -> List[UserChat]:
        """Get all chats for a user"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(UserChat)
                .options(selectinload(UserChat.last_message))
                .where(UserChat.user_id == user_id)
                .order_by(UserChat.last_interaction.desc())
            )
            return result.scalars().all()

    async def get_chat_history(self, user_id: int, peer_id: int) -> List[Message]:
        """Get chat history between two users"""
        async with self.async_session_factory() as session:
            result = await session.execute(
                select(Message)
                .options(selectinload(Message.sender))
                .options(selectinload(Message.recipient))
                .where(
                    or_(
                        and_(Message.sender_id == user_id, Message.recipient_id == peer_id),
                        and_(Message.sender_id == peer_id, Message.recipient_id == user_id)
                    )
                )
                .order_by(Message.timestamp.asc())
            )
            return result.scalars().all()

    async def update_user_chat(self, user_id: int, peer_id: int, message_id: int):
        """Update or create a chat record between two users"""
        async with self.async_session_factory() as session:
            chat = await session.execute(
                select(UserChat)
                .where(
                    and_(UserChat.user_id == user_id, UserChat.peer_id == peer_id)
                )
            )
            chat = chat.scalar_one_or_none()
            
            if chat:
                chat.last_message_id = message_id
                chat.last_interaction = datetime.utcnow()
            else:
                chat = UserChat(
                    user_id=user_id,
                    peer_id=peer_id,
                    last_message_id=message_id,
                    last_interaction=datetime.utcnow()
                )
                session.add(chat)
            
            await session.commit()

    async def update_user_status(self, user_id: int, is_online: bool):
        """Update user's online status and last seen timestamp"""
        async with self.async_session_factory() as session:
            user = await session.get(User, user_id)
            if user:
                user.is_online = is_online
                user.last_seen = datetime.utcnow()
                await session.commit()

    async def get_all_users(self) -> List[User]:
        """Get all users"""
        async with self.async_session_factory() as session:
            result = await session.execute(select(User))
            return result.scalars().all()
