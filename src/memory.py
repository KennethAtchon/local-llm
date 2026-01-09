#!/usr/bin/env python3
"""
Long-term memory system for the AI agent using SQLite
Stores conversation history persistently across sessions
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Database file location - store at project root, not in src/
_project_root = Path(__file__).parent.parent
MEMORY_DB_PATH = os.getenv("AGENT_MEMORY_DB", str(_project_root / "agent_memory.db"))


class AgentMemory:
    """Manages long-term memory for the AI agent using SQLite"""
    
    def __init__(self, db_path: str = MEMORY_DB_PATH):
        """Initialize the memory system with a SQLite database"""
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create the database and tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON conversations(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session 
            ON conversations(session_id)
        """)
        
        conn.commit()
        conn.close()
    
    def add_message(self, role: str, content: str, session_id: Optional[str] = None):
        """Add a message to the memory database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO conversations (timestamp, role, content, session_id)
            VALUES (?, ?, ?, ?)
        """, (timestamp, role, content, session_id))
        
        conn.commit()
        conn.close()
    
    def get_recent_messages(self, limit: int = 50) -> List[BaseMessage]:
        """
        Retrieve recent messages from memory and convert to LangChain messages
        
        Args:
            limit: Maximum number of messages to retrieve (default: 50)
        
        Returns:
            List of LangChain message objects (HumanMessage/AIMessage)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content 
            FROM conversations 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to LangChain messages (reverse to get chronological order)
        messages = []
        for role, content in reversed(rows):
            if role == "human":
                messages.append(HumanMessage(content=content))
            elif role == "ai":
                messages.append(AIMessage(content=content))
        
        return messages
    
    def get_session_messages(self, session_id: str) -> List[BaseMessage]:
        """Get all messages for a specific session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content 
            FROM conversations 
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for role, content in rows:
            if role == "human":
                messages.append(HumanMessage(content=content))
            elif role == "ai":
                messages.append(AIMessage(content=content))
        
        return messages
    
    def get_message_count(self) -> int:
        """Get the total number of messages stored"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def clear_memory(self):
        """Clear all stored conversations (use with caution!)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversations")
        conn.commit()
        conn.close()
    
    def search_messages(self, query: str, limit: int = 10) -> List[tuple]:
        """
        Search for messages containing the query text
        
        Returns:
            List of tuples (timestamp, role, content)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, role, content 
            FROM conversations 
            WHERE content LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (f"%{query}%", limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
