from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from Models import Conversation, Participant, Message, ParticipantRole, User
from Schemas import ConversationCreate, ConversationUpdate, ParticipantCreate
from typing import List, Optional
import uuid
from datetime import datetime
from Database import get_db

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"]
)

@router.post("/", response_model=ConversationCreate)
def create_conversation(conversation: ConversationCreate, creator_id: int, db: Session = Depends(get_db)):
    """Create a new conversation"""
    db_conversation = Conversation(
        name=conversation.name,
        description=conversation.description,
        type=conversation.type,
        is_private=conversation.is_private,
        created_by=creator_id,
        max_participants=conversation.max_participants
    )
    
    db.add(db_conversation)
    db.flush()  # Get the ID without committing
    
    # Add creator as owner
    creator_participant = Participant(
        conversation_id=db_conversation.id,
        user_id=creator_id,
        role=ParticipantRole.owner
    )
    db.add(creator_participant)
    
    # Add other participants
    for user_id in conversation.participant_ids:
        if user_id != creator_id:  # Don't add creator twice
            participant = Participant(
                conversation_id=db_conversation.id,
                user_id=user_id,
                role=ParticipantRole.member
            )
            db.add(participant)
    
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

@router.get("/{conversation_id}", response_model=Optional[ConversationCreate])
async def get_conversation(conversation_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get conversation if user is a participant"""
    conversation = db.query(Conversation).join(Participant).filter(
        Conversation.id == conversation_id,
        Participant.user_id == user_id,
        Participant.left_at.is_(None)
    ).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or user is not a participant"
        )
    return conversation

@router.get("/user/{user_id}", response_model=List[ConversationCreate])
async def get_user_conversations(user_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a user"""
    conversations = db.query(Conversation).join(Participant).filter(
        Participant.user_id == user_id,
        Participant.left_at.is_(None)
    ).order_by(Conversation.last_message_at.desc()).all()
    return conversations

@router.post("/{conversation_id}/participants", response_model=ParticipantCreate)
async def add_participant(conversation_id: int, user_id: int, added_by: int, db: Session = Depends(get_db)):
    """Add a participant to a conversation"""
    # Check if user adding has permission
    adder = db.query(Participant).filter(
        Participant.conversation_id == conversation_id,
        Participant.user_id == added_by,
        Participant.role.in_([ParticipantRole.owner, ParticipantRole.admin])
    ).first()
    
    if not adder:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Check if user is already a participant
    existing = db.query(Participant).filter(
        Participant.conversation_id == conversation_id,
        Participant.user_id == user_id
    ).first()
    
    if existing:
        if existing.left_at:
            # Rejoin conversation
            existing.left_at = None
            existing.joined_at = datetime.utcnow()
            db.commit()
            return existing
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a participant"
            )
    
    participant = Participant(
        conversation_id=conversation_id,
        user_id=user_id,
        role=ParticipantRole.member
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant

@router.delete("/{conversation_id}/participants/{user_id}")
async def remove_participant(conversation_id: int, user_id: int, removed_by: int, db: Session = Depends(get_db)):
    """Remove a participant from a conversation"""
    # Check permissions
    remover = db.query(Participant).filter(
        Participant.conversation_id == conversation_id,
        Participant.user_id == removed_by,
        Participant.role.in_([ParticipantRole.owner, ParticipantRole.admin])
    ).first()
    
    if not remover and removed_by != user_id:  # Can remove yourself
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    participant = db.query(Participant).filter(
        Participant.conversation_id == conversation_id,
        Participant.user_id == user_id,
        Participant.left_at.is_(None)
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )
    
    participant.left_at = datetime.utcnow()
    db.commit()
    return {"detail": "Participant removed successfully"}