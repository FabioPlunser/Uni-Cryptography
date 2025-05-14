from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from typing import Optional

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    public_key_b64 = Column(String)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)

    sent_messages = relationship(
        "Message", back_populates="sender", foreign_keys="Message.sender_id"
    )
    received_messages = relationship(
        "Message",
        back_populates="recipient",
        foreign_keys="Message.recipient_id",
    )
    chats = relationship(
        "UserChat", back_populates="user", foreign_keys="UserChat.user_id"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    message_number = Column(Integer, default=0)

    # Relationships
    sender = relationship(
        User, back_populates="sent_messages", foreign_keys=[sender_id]
    )
    recipient = relationship(
        User, back_populates="received_messages", foreign_keys=[recipient_id]
    )


class UserChat(Base):
    __tablename__ = "user_chats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    peer_id = Column(Integer, ForeignKey("users.id"))
    last_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    last_interaction = Column(DateTime, default=datetime.utcnow)

    # Relationships (commented out as in original)
    user = relationship("User", back_populates="chats", foreign_keys=[user_id])
    peer = relationship("User", foreign_keys=[peer_id])
    last_message = relationship("Message", foreign_keys=[last_message_id])


# Pydantic Models
class LastMessage(BaseModel):
    content: str
    timestamp: datetime
    is_mine: bool


class UserBase(BaseModel):
    id: int
    username: str
    is_online: bool = False
    last_seen: Optional[datetime] = None
    has_chat: Optional[bool] = None
    last_message: Optional[LastMessage] = None


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class PublicKeyUpdate(BaseModel):
    public_key: str


class PublicKeyResponse(BaseModel):
    username: str
    public_key: str


# Renamed Pydantic Message model
class MessageSchema(BaseModel):
    sender: str
    recipient: str
    content: str
    timestamp: Optional[datetime] = None  # Changed to datetime for consistency

    class Config:
        orm_mode = True  # or from_attributes = True for Pydantic v2
