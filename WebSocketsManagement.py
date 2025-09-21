# websocket_manager.py - WebSocket Connection Management (No UUID)
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Store user's conversations: {user_id: set of conversation_ids}
        self.user_conversations: Dict[str, Set[str]] = {}
        # Store conversation participants: {conversation_id: set of user_ids}
        self.conversation_participants: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        
        # Load user's conversations
        await self.load_user_conversations(user_id)
    
    def disconnect(self, user_id: str, connection_id: str):
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
    
    async def load_user_conversations(self, user_id: str):
        """Load user's conversations for broadcasting"""
        # This would typically query the database
        # For now, we'll implement a simple version
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
    
    def add_user_to_conversation(self, user_id: str, conversation_id: str):
        """Add user to conversation for broadcasting"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = set()
        
        self.user_conversations[user_id].add(conversation_id)
        
        if conversation_id not in self.conversation_participants:
            self.conversation_participants[conversation_id] = set()
        
        self.conversation_participants[conversation_id].add(user_id)
    
    def remove_user_from_conversation(self, user_id: str, conversation_id: str):
        """Remove user from conversation"""
        if user_id in self.user_conversations:
            self.user_conversations[user_id].discard(conversation_id)
            
        if conversation_id in self.conversation_participants:
            self.conversation_participants[conversation_id].discard(user_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            dead_connections = []
            for connection_id, websocket in self.active_connections[user_id].items():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception:
                    # Mark dead connection for removal
                    dead_connections.append(connection_id)
            
            # Clean up dead connections
            for connection_id in dead_connections:
                self.active_connections[user_id].pop(connection_id, None)
            
            # Remove user if no active connections left
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def broadcast_to_conversation(self, message: dict, conversation_id: str, exclude_user: str = None):
        """Broadcast message to all participants in a conversation"""
        if conversation_id in self.conversation_participants:
            for user_id in self.conversation_participants[conversation_id]:
                if user_id != exclude_user:
                    await self.send_personal_message(message, user_id)
    
    async def send_typing_indicator(self, conversation_id: str, user_id: str, is_typing: bool):
        """Send typing indicator to conversation participants"""
        message = {
            "event_type": "typing_start" if is_typing else "typing_stop",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_conversation(message, conversation_id, exclude_user=user_id)
    
    async def send_user_status(self, conversation_id: str, user_id: str, status: str):
        """Send user status (online/offline) to conversation participants"""
        message = {
            "event_type": "user_status_changed",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "status": status
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_conversation(message, conversation_id, exclude_user=user_id)
    
    def get_online_users(self, conversation_id: str) -> List[str]:
        """Get list of online users in a conversation"""
        if conversation_id in self.conversation_participants:
            return [
                user_id for user_id in self.conversation_participants[conversation_id]
                if user_id in self.active_connections
            ]
        return []
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        if user_id in self.active_connections:
            return len(self.active_connections[user_id])
        return 0
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if user has any active connections"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_conversation_online_count(self, conversation_id: str) -> int:
        """Get count of online users in a conversation"""
        return len(self.get_online_users(conversation_id))
    
    def get_all_online_users(self) -> List[str]:
        """Get all currently online users"""
        return list(self.active_connections.keys())
    
    def get_user_conversations(self, user_id: str) -> Set[str]:
        """Get all conversations a user is part of"""
        return self.user_conversations.get(user_id, set())
    
    def get_conversation_participants(self, conversation_id: str) -> Set[str]:
        """Get all participants in a conversation"""
        return self.conversation_participants.get(conversation_id, set())
    
    async def notify_user_joined_conversation(self, conversation_id: str, user_id: str):
        """Notify conversation participants that a user joined"""
        message = {
            "event_type": "user_joined_conversation",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_conversation(message, conversation_id, exclude_user=user_id)
    
    async def notify_user_left_conversation(self, conversation_id: str, user_id: str):
        """Notify conversation participants that a user left"""
        message = {
            "event_type": "user_left_conversation",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_conversation(message, conversation_id, exclude_user=user_id)
    
    def cleanup_dead_connections(self):
        """Clean up any dead connections (can be called periodically)"""
        users_to_remove = []
        
        for user_id, connections in self.active_connections.items():
            dead_connections = []
            
            for connection_id, websocket in connections.items():
                # You can implement a ping/pong mechanism here to check if connection is alive
                # For now, we'll just keep this method for manual cleanup
                pass
            
            # Remove dead connections
            for connection_id in dead_connections:
                connections.pop(connection_id, None)
            
            # Mark user for removal if no connections left
            if not connections:
                users_to_remove.append(user_id)
        
        # Remove users with no connections
        for user_id in users_to_remove:
            self.disconnect_all_user_connections(user_id)
    
    def disconnect_all_user_connections(self, user_id: str):
        """Disconnect all connections for a user"""
        if user_id in self.active_connections:
            # Close all WebSocket connections for this user
            for websocket in self.active_connections[user_id].values():
                try:
                    # Note: You might want to send a close message before closing
                    pass
                except Exception:
                    pass
            
            del self.active_connections[user_id]
            
            # Remove from all conversations
            if user_id in self.user_conversations:
                for conv_id in self.user_conversations[user_id]:
                    if conv_id in self.conversation_participants:
                        self.conversation_participants[conv_id].discard(user_id)
                del self.user_conversations[user_id]
    
    def get_stats(self) -> dict:
        """Get connection manager statistics"""
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        
        return {
            "total_users_online": len(self.active_connections),
            "total_connections": total_connections,
            "total_conversations": len(self.conversation_participants),
            "average_connections_per_user": total_connections / max(1, len(self.active_connections))
        }

# Global connection manager instance
connection_manager = ConnectionManager()