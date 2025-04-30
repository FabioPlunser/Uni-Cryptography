# src/db_utils.py

import asyncio
import base64
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- Database Setup ---
Base = declarative_base()
DATABASE_FILE = "murmly.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"  # Use aiosqlite driver


# --- Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    public_key_b64 = Column(String, unique=True, nullable=False)
    is_online = Column(Boolean, default=False, index=True)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    registration_date = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    encrypted_content_b64 = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.time, index=True)


# --- Database Interaction Class ---
class Database:
    def __init__(self, db_url=DATABASE_URL):
        # echo=False is usually preferred for production/less verbose logs
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        logging.info(f"Async database engine created for {db_url}")

    async def init_db(self):
        """Initializes the database and creates tables if they don't exist."""
        async with self.engine.begin() as conn:
            logging.info("Running metadata create_all...")
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Database tables ensured.")

    # --- User Operations ---
    async def create_user(
        self, username: str, public_key_bytes: bytes
    ) -> Optional[User]:
        """Creates a new user, storing the public key as Base64."""
        public_key_b64 = base64.b64encode(public_key_bytes).decode("ascii")
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt_exists = select(User).where(
                    (User.username == username)
                    | (User.public_key_b64 == public_key_b64)
                )
                existing_user_res = await session.execute(stmt_exists)
                if existing_user_res.scalars().first():
                    logging.warning(
                        f"User '{username}' or their public key already exists."
                    )
                    return None

                new_user = User(username=username, public_key_b64=public_key_b64)
                session.add(new_user)
                await session.flush()
                logging.info(f"Attempting to commit new user '{username}'")
            logging.info(
                f"Successfully created user '{username}' with id {new_user.id}"
            )
            return new_user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        async with self.async_session_factory() as session:
            stmt = select(User).where(User.username == username)
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

    async def get_online_users(self) -> List[str]:
        """Retrieves a list of usernames for all online users."""
        async with self.async_session_factory() as session:
            stmt = (
                select(User.username)
                .where(User.is_online == True)
                .order_by(User.username)
            )
            result = await session.execute(stmt)
            online_usernames = result.scalars().all()
            return online_usernames

    async def set_user_online_status(self, username: str, is_online: bool) -> bool:
        """Updates the online status and last_seen for a user."""
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt = (
                    update(User)
                    .where(User.username == username)
                    .values(is_online=is_online, last_seen=datetime.utcnow())
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    logging.warning(
                        f"Attempted to update status for non-existent user '{username}'"
                    )
                    return False
                else:
                    logging.debug(f"Set user '{username}' online status to {is_online}")
                    return True

    async def mark_all_offline(self):
        """Marks all users as offline, typically on server startup."""
        async with self.async_session_factory() as session:
            async with session.begin():
                stmt = (
                    update(User)
                    .where(User.is_online == True)
                    .values(is_online=False, last_seen=datetime.utcnow())
                    .execution_options(synchronize_session=False)
                )
                result = await session.execute(stmt)
                logging.info(f"Marked {result.rowcount} users as offline.")

    # --- Message Operations ---
    async def store_message(
        self, sender_username: str, recipient_username: str, encrypted_content_b64: str
    ) -> Optional[Message]:
        """Stores an encrypted message, looking up user IDs first."""
        async with self.async_session_factory() as session:
            async with session.begin():
                sender = await self._get_user_id(session, sender_username)
                recipient = await self._get_user_id(session, recipient_username)

                if sender is None or recipient is None:
                    logging.error(
                        f"Could not store message: Sender '{sender_username}' or Recipient '{recipient_username}' not found."
                    )
                    return None

                new_message = Message(
                    sender_id=sender.id,
                    recipient_id=recipient.id,
                    encrypted_content_b64=encrypted_content_b64,
                )
                session.add(new_message)
                await session.flush()
            logging.debug(
                f"Stored message from '{sender_username}' to '{recipient_username}'"
            )
            return new_message

    async def _get_user_id(
        self, session: AsyncSession, username: str
    ) -> Optional[User]:
        """Helper to get user object within an existing session."""
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalars().first()


# --- Authentication Function (Async) ---
async def authenticate_user_by_key_async(
    db: Database, username: str, key_bytes_provided: bytes
) -> bool:
    """Authenticates a user by checking their username and public key using the Database class."""
    user = await db.get_user_by_username(username)
    if user:
        try:
            stored_key_b64 = user.public_key_b64
            stored_key_bytes = base64.b64decode(stored_key_b64)

            # Direct byte comparison is sufficient and secure for public keys
            if stored_key_bytes == key_bytes_provided:
                logging.debug(f"Public key match for user '{username}'")
                return True
            else:
                logging.warning(f"Public key mismatch for user '{username}'")
                return False
        except Exception as e:
            logging.error(f"Error decoding/comparing key for user '{username}': {e}")
            return False
    else:
        # Auto registration if user not found
        logging.warning(f"User '{username}' not found. Attempting auto-registration.")
        try:
            created_user = await db.create_user(username, key_bytes_provided)
            return created_user is not None
        except Exception as e:
            logging.error(f"Failed to auto-register '{username}': {e}")
            return False


# --- Synchronous Wrapper (Needed for current threading model) ---
def authenticate_user_by_key_sync(
    db: Database, username: str, key_bytes_provided: bytes
) -> bool:
    """Synchronous wrapper to call the async authentication function."""
    try:
        return asyncio.run(
            authenticate_user_by_key_async(db, username, key_bytes_provided)
        )
    except RuntimeError as e:
        logging.error(
            f"RuntimeError calling async auth for '{username}': {e}. Trying get_event_loop."
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logging.warning(
                    "Cannot run nested asyncio loop easily from sync thread."
                )
                return False
            else:
                return loop.run_until_complete(
                    authenticate_user_by_key_async(db, username, key_bytes_provided)
                )
        except Exception as inner_e:
            logging.error(
                f"Failed to run async auth even with get_event_loop for '{username}': {inner_e}"
            )
            return False
    except Exception as e:
        logging.error(
            f"Unexpected error in sync wrapper for async auth '{username}': {e}"
        )
        return False
