
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import uuid
import json
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[uuid.UUID, Dict[str, WebSocket]] = {}
        # Store user's conversations: {user_id: set of conversation_ids}
        self.user_conversations: Dict[uuid.UUID, Set[uuid.UUID]] = {}
        # Store conversation participants: {conversation_id: set of user_ids}
        self.conversation_participants: Dict[uuid.UUID, Set[uuid.UUID]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: uuid.UUID, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        
        # Load user's conversations
        await self.load_user_conversations(user_id)
    
    def disconnect(self, user_id: uuid.UUID, connection_id: str):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(connection_id, None)
            
            # Remove user if no active connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
                # Remove from conversation participants
                if user_id in self.user_conversations:
                    for conv_id in self.user_conversations[user_id]:
                        if conv_id in self.conversation_participants:
                            self.conversation_participants[conv_id].discard(user_id)
                    del self.user_conversations[user_id]
    
    async def load_user_conversations(self, user_id: uuid.UUID):
        """Load user's conversations for broadcasting"""
        # This would typically query the database
        # For now, we'll implement a simple version
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
    
    def add_user_to_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID):
        """Add user to conversation for broadcasting"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        
        self.user_conversations[user_id].add(conversation_id)
        
        if conversation_id not in self.conversation_participants:
            self.conversation_participants[conversation_id] = set()
        
        self.conversation_participants[conversation_id].add(user_id)
    
    async def send_personal_message(self, message: dict, user_id: uuid.UUID):
        """Send message to specific user"""
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id].values():
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    # Connection is dead, will be cleaned up later
                    pass
    
    async def broadcast_to_conversation(self, message: dict, conversation_id: uuid.UUID, exclude_user: uuid.UUID = None):
        """Broadcast message to all participants in a conversation"""
        if conversation_id in self.conversation_participants:
            for user_id in self.conversation_participants[conversation_id]:
                if user_id != exclude_user:
                    await self.send_personal_message(message, user_id)
    
    async def send_typing_indicator(self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_typing: bool):
        """Send typing indicator to conversation participants"""
        message = {
            "event_type": "typing_start" if is_typing else "typing_stop",
            "data": {
                "conversation_id": str(conversation_id),
                "user_id": str(user_id)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_conversation(message, conversation_id, exclude_user=user_id)
    
    def get_online_users(self, conversation_id: uuid.UUID) -> List[uuid.UUID]:
        """Get list of online users in a conversation"""
        if conversation_id in self.conversation_participants:
            return [
                user_id for user_id in self.conversation_participants[conversation_id]
                if user_id in self.active_connections
            ]
        return []

# Global connection manager instance
connection_manager = ConnectionManager()
