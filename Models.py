from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Enum as SqlEnum, Table, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import CITEXT  # Optional: for PostgreSQL
from typing import Optional
import enum
from database import Base
from datetime import datetime
from fastapi import WebSocket, Depends
from sqlalchemy.orm import Session



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

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str] = mapped_column(String(500))
    bio: Mapped[str] = mapped_column(Text)
    is_active: Mapped[str] = mapped_column(Boolean, default=True)
    is_verified: Mapped[str] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[str] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at: Mapped[str] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")
    
    # Relationships
    messages = relationship("Message", back_populates="sender")
    created_conversations = relationship("Conversation", back_populates="creator")
    participants = relationship("Participant", back_populates="user")
    reactions = relationship("MessageReaction", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    blocked_users = relationship("BlockedUser", foreign_keys="BlockedUser.blocker_id", back_populates="blocker")
    blocked_by = relationship("BlockedUser", foreign_keys="BlockedUser.blocked_id", back_populates="blocked")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    description = Column(Text)
    type = Column(Enum(ConversationType), nullable=False)
    is_private = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow, index=True)
    max_participants = Column(Integer)
    settings = Column(JSON, default=dict)
    
    # Relationships
    creator = relationship("User", back_populates="created_conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text)
    message_type = Column(Enum(MessageType), default=MessageType.text)
    meta_data = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    edited_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)

    # self-referencing field (reply-to)
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages")
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")
    attachments = relationship("FileAttachment", back_populates="message", cascade="all, delete-orphan")

    # Reply-to relationship
    reply_to = relationship("Message", remote_side=[id])

   
class Participant(Base):
    __tablename__ = "participants"
    
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(Enum(ParticipantRole), default=ParticipantRole.member)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime)
    last_read_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    is_muted = Column(Boolean, default=False)
    permissions = Column(JSON, default=dict)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="participants")
    last_read_message = relationship("Message")

class MessageReaction(Base):
    __tablename__ = "message_reactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reaction = Column(String(10), nullable=False)  # emoji or reaction type
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="reactions")
    user = relationship("User", back_populates="reactions")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint("user_id", "message_id", name="uq_user_message"),
    )

class FileAttachment(Base):
    __tablename__ = "file_attachments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    thumbnail_url = Column(String(500))
    upload_status = Column(Enum(UploadStatus), default=UploadStatus.uploading, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="attachments")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    connection_id = Column(String(255))
    device_info = Column(JSON, default=dict)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class BlockedUser(Base):
    __tablename__ = "blocked_users"
    
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String(255))
    
    # Relationships
    blocker = relationship("User", foreign_keys=[blocker_id], back_populates="blocked_users")
    blocked = relationship("User", foreign_keys=[blocked_id], back_populates="blocked_by")

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    notification_settings = Column(JSON, default={
        "message_notifications": True,
        "email_notifications": False,
        "push_notifications": True,
        "sound_enabled": True
    })
    privacy_settings = Column(JSON, default={
        "show_online_status": True,
        "allow_direct_messages": True,
        "show_read_receipts": True
    })
    theme_preference = Column(String(20), default="light")
    message_preview = Column(Boolean, default=True)
    online_status_visible = Column(Boolean, default=True)
    read_receipts_enabled = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="preferences")


