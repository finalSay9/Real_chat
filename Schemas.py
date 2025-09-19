from datetime import datetime
from typing import List, Optional
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