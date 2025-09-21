# websocket_routes.py - Updated WebSocket Routes (No UUID)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from Database import get_db
from WebSocketsManagement import connection_manager
from Security import verify_token
import Users
import Messages
from Schemas import MessageSendEvent, TypingEvent, WSEventType
import json
from datetime import datetime

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time communication"""
    if not token:
        await websocket.close(code=1008, reason="Token required")
        return
    
    try:
        user_id = verify_token(token)
        # Convert UUID to string if your verify_token returns UUID
        user_id_str = str(user_id)
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Generate connection ID
    import secrets
    connection_id = secrets.token_urlsafe(16)
    
    # Connect user
    await connection_manager.connect(websocket, user_id_str, connection_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            event_type = message_data.get("event_type")
            event_data = message_data.get("data", {})
            
            # Handle different event types
            await handle_websocket_event(event_type, event_data, user_id_str, websocket)
            
    except WebSocketDisconnect:
        connection_manager.disconnect(user_id_str, connection_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connection_manager.disconnect(user_id_str, connection_id)

async def handle_websocket_event(event_type: str, data: dict, user_id: str, websocket: WebSocket):
    """Handle different WebSocket events"""
    db = next(get_db())
    
    try:
        if event_type == "message_send":
            await handle_message_send(data, user_id, db)
        elif event_type == "typing_start":
            await handle_typing_start(data, user_id)
        elif event_type == "typing_stop":
            await handle_typing_stop(data, user_id)
        elif event_type == "join_conversation":
            await handle_join_conversation(data, user_id, db)
        elif event_type == "leave_conversation":
            await handle_leave_conversation(data, user_id)
        else:
            # Unknown event type
            error_message = {
                "event_type": "error",
                "data": {"message": f"Unknown event type: {event_type}"},
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(error_message))
    
    except Exception as e:
        error_message = {
            "event_type": "error",
            "data": {"message": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_message))
    
    finally:
        db.close()

async def handle_message_send(data: dict, user_id: str, db: Session):
    """Handle message send event"""
    try:
        conversation_id = data.get("conversation_id")
        content = data.get("content")
        message_type = data.get("message_type", "text")
        reply_to_message_id = data.get("reply_to_message_id")
        
        if not conversation_id or not content:
            raise ValueError("conversation_id and content are required")
        
        # Create message in database (you'll need to update your CRUD to use strings)
        # db_message = Messages.create_message(db, message_create, user_id)
        
        # Get sender info
        # sender = Users.get_user(db, user_id)
        
        # Broadcast to conversation participants
        message_data = {
            "event_type": "message_received",
            "data": {
                "conversation_id": conversation_id,
                "sender_id": user_id,
                "content": content,
                "message_type": message_type,
                "created_at": datetime.utcnow().isoformat(),
                "reply_to_message_id": reply_to_message_id,
                # "sender": {
                #     "id": sender.id,
                #     "username": sender.username,
                #     "display_name": sender.display_name,
                #     "avatar_url": sender.avatar_url
                # }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await connection_manager.broadcast_to_conversation(
            message_data,
            conversation_id,
            exclude_user=user_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def handle_typing_start(data: dict, user_id: str):
    """Handle typing start event"""
    conversation_id = data.get("conversation_id")
    if conversation_id:
        await connection_manager.send_typing_indicator(
            conversation_id, 
            user_id, 
            is_typing=True
        )

async def handle_typing_stop(data: dict, user_id: str):
    """Handle typing stop event"""
    conversation_id = data.get("conversation_id")
    if conversation_id:
        await connection_manager.send_typing_indicator(
            conversation_id, 
            user_id, 
            is_typing=False
        )

async def handle_join_conversation(data: dict, user_id: str, db: Session):
    """Handle join conversation event"""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    
    # Verify user is participant (you'll need to update your CRUD to use strings)
    # conversation = Conversations.get_conversation(db, conversation_id, user_id)
    
    # if conversation:
    connection_manager.add_user_to_conversation(user_id, conversation_id)
    await connection_manager.notify_user_joined_conversation(conversation_id, user_id)

async def handle_leave_conversation(data: dict, user_id: str):
    """Handle leave conversation event"""
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    
    await connection_manager.notify_user_left_conversation(conversation_id, user_id)
    connection_manager.remove_user_from_conversation(user_id, conversation_id)