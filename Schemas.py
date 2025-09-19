from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict,Field
from enum import Enum
import re
from pydantic_core.core_schema import ValidationInfo



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