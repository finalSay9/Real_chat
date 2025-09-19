from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from Models import Message, Conversation, Participant
from Schemas import MessageCreate, MessageUpdate
from typing import List, Optional
import uuid
from datetime import datetime
from Database import get_db

router = APIRouter(
    prefix="/messages",
    tags=["messages"]
)

@router.post("/", response_model=MessageCreate)
async def create_message(message: MessageCreate, sender_id: int, db: Session = Depends(get_db)):
    """Create a new message"""
    # Verify sender is participant
    participant = db.query(Participant).filter(
        Participant.conversation_id == message.conversation_id,
        Participant.user_id == sender_id,
        Participant.left_at.is_(None)
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    db_message = Message(
        conversation_id=message.conversation_id,
        sender_id=sender_id,
        content=message.content,
        message_type=message.message_type,
        metadata=message.metadata,
        reply_to_message_id=message.reply_to_message_id
    )
    
    db.add(db_message)
    
    # Update conversation last message time
    conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
    if conversation:
        conversation.last_message_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    return db_message

@router.get("/conversation/{conversation_id}", response_model=List[MessageCreate])
async def get_messages(conversation_id: int, user_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Get messages from a conversation"""
    # Verify user is participant
    participant = db.query(Participant).filter(
        Participant.conversation_id == conversation_id,
        Participant.user_id == user_id,
        Participant.left_at.is_(None)
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
    return messages

@router.put("/{message_id}", response_model=MessageCreate)
async def update_message(message_id: int, message_update: MessageUpdate, user_id: int, db: Session = Depends(get_db)):
    """Update a message"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.sender_id == user_id,
        Message.is_deleted == False
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or permission denied"
        )
    
    update_data = message_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(message, field, value)
    
    message.updated_at = datetime.utcnow()
    message.edited_at = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message

@router.delete("/{message_id}", response_model=MessageCreate)
async def delete_message(message_id: int, user_id:int, db: Session = Depends(get_db)):
    """Soft delete a message"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.sender_id == user_id,
        Message.is_deleted == False
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or permission denied"
        )
    
    message.is_deleted = True
    message.content = "[Message deleted]"
    message.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message

@router.post("/{conversation_id}/read/{message_id}")
async def mark_as_read(conversation_id: int, message_id: int, user_id: int, db: Session = Depends(get_db)):
    """Mark message as read by user"""
    participant = db.query(Participant).filter(
        Participant.conversation_id == conversation_id,
        Participant.user_id == user_id
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    participant.last_read_message_id = message_id
    db.commit()
    return {"detail": "Message marked as read"}