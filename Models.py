from sqlalchemy import JSON, BigInteger, Column, ForeignKey, Integer, String, Boolean, DateTime, Enum as SqlEnum, Table, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import CITEXT  # Optional: for PostgreSQL
from typing import Optional
import enum
from Database import Base
from datetime import datetime
from fastapi import WebSocket, Depends
from sqlalchemy.orm import Session
from sqlalchemy import Enum



# Enums
class ConversationType(str, enum.Enum):
    direct_message = "direct_message"
    group_chat = "group_chat"
    channel = "channel"

class MessageType(str, enum.Enum):
    text = "text"
    image = "image"
    file = "file"
    system = "system"
    deleted = "deleted"

class ParticipantRole(str, enum.Enum):
    member = "member"
    admin = "admin"
    owner = "owner"
    moderator = "moderator"

class UploadStatus(str, enum.Enum):
    uploading = "uploading"
    completed = "completed"
    failed = "failed"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str] = mapped_column(String(500))
    bio: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")
    
    # Relationships
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="sender")
    created_conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="creator")
    participants: Mapped[list["Participant"]] = relationship("Participant", back_populates="user")
    reactions: Mapped[list["MessageReaction"]] = relationship("MessageReaction", back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user")
    blocked_users: Mapped[list["BlockedUser"]] = relationship("BlockedUser", foreign_keys="BlockedUser.blocker_id", back_populates="blocker")
    blocked_by: Mapped[list["BlockedUser"]] = relationship("BlockedUser", foreign_keys="BlockedUser.blocked_id", back_populates="blocked")
    preferences: Mapped["UserPreferences"] = relationship("UserPreferences", back_populates="user", uselist=False)


class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped["ConversationType"] = mapped_column(Enum(ConversationType), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    max_participants: Mapped[int] = mapped_column(Integer)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="created_conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    participants: Mapped[list["Participant"]] = relationship("Participant", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped["MessageType"] = mapped_column(Enum(MessageType), default=MessageType.text)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    edited_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # self-referencing field (reply-to)
    reply_to_message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User", back_populates="messages")
    reactions: Mapped[list["MessageReaction"]] = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")
    attachments: Mapped[list["FileAttachment"]] = relationship("FileAttachment", back_populates="message", cascade="all, delete-orphan")

    # Reply-to relationship
    reply_to: Mapped["Message"] = relationship("Message", remote_side=[id])


class Participant(Base):
    __tablename__ = "participants"
    
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    role: Mapped["ParticipantRole"] = mapped_column(Enum(ParticipantRole), default=ParticipantRole.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    left_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_read_message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="participants")
    last_read_message: Mapped["Message"] = relationship("Message")


class MessageReaction(Base):
    __tablename__ = "message_reactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    reaction: Mapped[str] = mapped_column(String(10), nullable=False)  # emoji or reaction type
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="reactions")
    user: Mapped["User"] = relationship("User", back_populates="reactions")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint("user_id", "message_id", name="uq_user_message"),
    )


class FileAttachment(Base):
    __tablename__ = "file_attachments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500))
    upload_status: Mapped["UploadStatus"] = mapped_column(Enum(UploadStatus), default=UploadStatus.uploading, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="attachments")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String(255))
    device_info: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")


class BlockedUser(Base):
    __tablename__ = "blocked_users"
    
    blocker_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    blocked_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reason: Mapped[str] = mapped_column(String(255))
    
    # Relationships
    blocker: Mapped["User"] = relationship("User", foreign_keys=[blocker_id], back_populates="blocked_users")
    blocked: Mapped["User"] = relationship("User", foreign_keys=[blocked_id], back_populates="blocked_by")


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    notification_settings: Mapped[dict] = mapped_column(JSON, default={
        "message_notifications": True,
        "email_notifications": False,
        "push_notifications": True,
        "sound_enabled": True
    })
    privacy_settings: Mapped[dict] = mapped_column(JSON, default={
        "show_online_status": True,
        "allow_direct_messages": True,
        "show_read_receipts": True
    })
    theme_preference: Mapped[str] = mapped_column(String(20), default="light")
    message_preview: Mapped[bool] = mapped_column(Boolean, default=True)
    online_status_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    read_receipts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")