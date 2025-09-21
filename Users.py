from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
import Models
import Schemas
from Security import get_password_hash
from typing import Optional, List
import uuid
from datetime import datetime
from Database import get_db
import Auth

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/", response_model=Schemas.UserResponse)
async def create_user(user: Schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if user already exists
    existing_user = db.query(Models.User).filter(
        or_(Models.User.email == user.email, Models.User.username == user.username)
    ).first()
    
    if existing_user:
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create user
    hashed_password = get_password_hash(user.password)
    db_user = Models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        display_name=user.display_name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        timezone=user.timezone,
        language=user.language
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create default preferences
    preferences = Models.UserPreferences(user_id=db_user.id)
    db.add(preferences)
    db.commit()
    
    return db_user

@router.get("/me", response_model=Schemas.UserResponse)
async def get_current_user_data(current_user: Models.User = Depends(Auth.get_current_user)):
    return current_user

@router.get("/{user_id}", response_model=Optional[Schemas.UserResponse])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(Models.User).filter(Models.User.id == user_id, Models.User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/email/{email}", response_model=Optional[Schemas.UserResponse])
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Get user by email"""
    user = db.query(Models.User).filter(Models.User.email == email, Models.User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/username/{username}", response_model=Optional[Schemas.UserResponse])
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """Get user by username"""
    user =  db.query(Models.User).filter(Models.User.username == username, Models.User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user

    

@router.put("/{user_id}", response_model=Schemas.UserResponse)
async def update_user(user_id: uuid.UUID, user_update: Schemas.UserUpdate, db: Session = Depends(get_db)):
    """Update user information"""
    user = db.query(Models.User).filter(Models.User.id == user_id, Models.User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user

@router.get("/search/", response_model=List[Schemas.UserPublic])
async def search_users(query: str, limit: int = 20, db: Session = Depends(get_db)):
    """Search users by username or display name"""
    users = db.query(Models.User).filter(
        or_(
            Models.User.username.ilike(f"%{query}%"),
            Models.User.display_name.ilike(f"%{query}%")
        ),
        Models.User.is_active == True
    ).limit(limit).all()
    return users

@router.delete("/{user_id}", response_model=Schemas.UserResponse)
async def deactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Deactivate user account"""
    user = db.query(Models.User).filter(Models.User.id == user_id, Models.User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user




