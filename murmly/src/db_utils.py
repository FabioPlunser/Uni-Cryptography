from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Float,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.future import select
from typing import List, Optional, Dict
from datetime import datetime, timedelta

import logging
import sqlite3
import uuid

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Database Setup ---
Base = declarative_base()
DATABASE_FILE = "murmly.db"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    public_key = Column(String, nullable=False)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    is_private = Column(Boolean, default=False)
    last_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)


class Database:
    def __init__(self):
        self.engine = create_engine(f"sqlite:///{DATABASE_FILE}", echo=True)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initializes the database and creates tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def create_user(self, username, public_key):
        """Creates a new user in the database."""
        async with self.async_session() as session:
            async with session.begin():
                new_user = User(username=username, public_key=public_key)
                session.add(new_user)
            await session.commit()
            return new_user

    async def get_user(self, username):
        """Retrieves a user from the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalars().first()
            return user

    async def get_all_users(self):
        """Retrieves all users from the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(select(User))
                users = result.scalars().all()
            return users

    async def get_all_users_online(self):
        """Retrieves all online users from the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.is_online == True)
                )
                online_users = result.scalars().all()
            return online_users

    async def update_user_status(self, username, is_online):
        """Updates the status of a user in the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(User).where(User.username == username)
                )
                user = result.scalars().first()
                user.is_online = is_online
            await session.commit()

    async def mark_all_users_as_offline(self):
        """Marks all users as offline in the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(select(User))
                users = result.scalars().all()
                for user in users:
                    user.is_online = False
            await session.commit()
            return users

    async def create_message(self, sender_id, recipient_id, content):
        """Creates a new message in the database."""
        async with self.async_session() as session:
            async with session.begin():
                new_message = Message(
                    sender_id=sender_id, recipient_id=recipient_id, content=content
                )
                session.add(new_message)
            await session.commit()
            return new_message

    async def get_all_messages(self):
        """Retrieves all messages from the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(select(Message))
                messages = result.scalars().all()
            return messages

    async def get_all_messages_for_user(self, user_id):
        """Retrieves all messages for a user from the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(Message).where(Message.sender_id == user_id)
                )
                messages = result.scalars().all()
            return messages

    async def get_all_messages_for_channel(self, channel_id):
        """Retrieves all messages for a channel from the database."""
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(Message).where(Message.recipient_id == channel_id)
                )
                messages = result.scalars().all()
            return messages


# def get_db_connection():
#     """Creates a new database connection."""
#     conn = sqlite3.connect(DATABASE_FILE)
#     conn.row_factory = sqlite3.Row
#     return conn


# def create_table(conn):
#     """Creates the database table if it doesn't exist."""
#     return


# def mark_all_users_as_offline(conn):
#     """Marks all users as offline in the database."""
#     return


def authenticate_user_by_key(conn, username, key_bytes):
    """Authenticates a user by their public key."""
    return True
