from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict,Field
from enum import Enum
import re
from pydantic_core.core_schema import ValidationInfo
import enum



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


class UserBase(BaseModel):
    username: str 
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"

    @field_validator('username')
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", value):
            raise ValueError("Username must be 3-20 characters long and contain only letters, numbers, or underscores")
        return value
    
    @field_validator('email')
    def normalize_email(cls, value: EmailStr) -> str:
        return value.lower()



class UserCreate(UserBase):
   
    password: str
    


    @field_validator('password')
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError('password must be 8 characters long')
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character")
        return value
    

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class UserResponse(UserBase):
    
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)



class UserPublic(BaseModel):
    
    
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)



# Conversation Schemas
class ConversationBase(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: ConversationType
    is_private: bool = True
    max_participants: Optional[int] = None

class ConversationCreate(ConversationBase):
    participant_ids: List[int] = []

class ConversationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_private: Optional[bool] = None
    max_participants: Optional[int] = None

class ConversationResponse(ConversationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id:int
    created_by: int
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    settings: Dict[str, Any]

# Message Schemas
class MessageBase(BaseModel):
    content: Optional[str] = Field(None, max_length=4000)
    message_type: MessageType = MessageType.text
    meta_data: Dict[str, Any] = {}
    reply_to_message_id: Optional[int] = None

class MessageCreate(MessageBase):
    conversation_id: int

class MessageUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=4000)
    meta_data: Optional[Dict[str, Any]] = None

class MessageResponse(MessageBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    conversation_id: int
    sender_id: int
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime]
    is_deleted: bool
    sender: UserPublic

# Participant Schemas
class ParticipantBase(BaseModel):
    role: ParticipantRole = ParticipantRole.member
    is_muted: bool = False
    permissions: Dict[str, Any] = {}

class ParticipantCreate(ParticipantBase):
    user_id: int
    conversation_id: int

class ParticipantUpdate(BaseModel):
    role: Optional[ParticipantRole] = None
    is_muted: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None

class ParticipantResponse(ParticipantBase):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    conversation_id: int
    joined_at: datetime
    left_at: Optional[datetime]
    last_read_message_id: Optional[int]
    user: UserPublic

# Reaction Schemas
class ReactionCreate(BaseModel):
    message_id: int
    reaction: str = Field(..., min_length=1, max_length=10)

class ReactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    message_id: int
    user_id: int
    reaction: str
    created_at: datetime
    user: UserPublic

# File Attachment Schemas
class FileAttachmentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int
    thumbnail_url: Optional[str] = None

class FileAttachmentCreate(FileAttachmentBase):
    message_id: int
    file_url: str

class FileAttachmentResponse(FileAttachmentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    message_id: int
    file_url: str
    upload_status: UploadStatus
    created_at: datetime

# WebSocket Event Schemas
class WSEventType(str, enum.Enum):
    message_send = "message_send"
    message_received = "message_received"
    typing_start = "typing_start"
    typing_stop = "typing_stop"
    user_joined = "user_joined"
    user_left = "user_left"
    delivery_status = "delivery_status"
    reaction_added = "reaction_added"
    reaction_removed = "reaction_removed"

class WSMessage(BaseModel):
    event_type: WSEventType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageSendEvent(BaseModel):
    conversation_id: int
    content: str
    message_type: MessageType = MessageType.text
    reply_to_message_id: Optional[int] = None

class TypingEvent(BaseModel):
    conversation_id: int

class UserPresenceEvent(BaseModel):
    conversation_id: int
    user_id: int

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

# Pagination Schemas
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

# User Preferences Schemas
class NotificationSettings(BaseModel):
    message_notifications: bool = True
    email_notifications: bool = False
    push_notifications: bool = True
    sound_enabled: bool = True

class PrivacySettings(BaseModel):
    show_online_status: bool = True
    allow_direct_messages: bool = True
    show_read_receipts: bool = True

class UserPreferencesUpdate(BaseModel):
    notification_settings: Optional[NotificationSettings] = None
    privacy_settings: Optional[PrivacySettings] = None
    theme_preference: Optional[str] = "light"
    message_preview: Optional[bool] = True
    online_status_visible: Optional[bool] = True
    read_receipts_enabled: Optional[bool] = True

class UserPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    notification_settings: Dict[str, Any]
    privacy_settings: Dict[str, Any]
    theme_preference: str
    message_preview: bool
    online_status_visible: bool
    read_receipts_enabled: bool