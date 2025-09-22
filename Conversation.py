# routers/conversations.py - Fixed Conversations Router
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from Database import get_db
from Schemas import ConversationCreate, ConversationResponse, ConversationUpdate, ParticipantResponse
from Models import User, Conversation, Participant
import Conversations as ConversationCRUD  # Your CRUD operations
from Security import get_current_user  # Updated import path
from typing import List
import uuid

# IMPORTANT: Don't add trailing slash in prefix!
router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("/", response_model=List[ConversationResponse])
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for current user"""
    try:
        conversations = ConversationCRUD.get_user_conversations(db, str(current_user.id))
        return conversations
    except Exception as e:
        print(f"Error getting conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    try:
        return ConversationCRUD.create_conversation(db, conversation, str(current_user.id))
    except Exception as e:
        print(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,  # Changed from UUID to string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        conversation = ConversationCRUD.get_conversation(db, conversation_id, str(current_user.id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )

@router.get("/{conversation_id}/participants", response_model=List[ParticipantResponse])
async def get_conversation_participants(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get participants of a conversation"""
    try:
        # Verify user has access to conversation
        conversation = ConversationCRUD.get_conversation(db, conversation_id, str(current_user.id))
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        participants = ConversationCRUD.get_conversation_participants(db, conversation_id)
        return participants
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting participants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve participants"
        )

@router.post("/{conversation_id}/participants/{user_id}")
async def add_participant(
    conversation_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add participant to conversation"""
    try:
        return ConversationCRUD.add_participant(db, conversation_id, user_id, str(current_user.id))
    except Exception as e:
        print(f"Error adding participant: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{conversation_id}/participants/{user_id}")
async def remove_participant(
    conversation_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove participant from conversation"""
    try:
        ConversationCRUD.remove_participant(db, conversation_id, user_id, str(current_user.id))
        return {"message": "Participant removed successfully"}
    except Exception as e:
        print(f"Error removing participant: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation (owner only)"""
    try:
        ConversationCRUD.delete_conversation(db, conversation_id, str(current_user.id))
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )