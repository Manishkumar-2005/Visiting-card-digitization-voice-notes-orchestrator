import os
import logging
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config import settings

# Try to import MongoDB client
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    HAS_MONGODB = True
except ImportError:
    HAS_MONGODB = False

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.is_mongo = False
        self.mongo_client = None
        self.db = None
        
        # SQLite Fallback configuration
        self.sqlite_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "local_database.sqlite"
        )
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)

        if HAS_MONGODB and settings.is_mongodb_configured:
            try:
                # 5 second timeout to avoid hanging if host is unreachable
                self.mongo_client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
                self.db = self.mongo_client[settings.DB_NAME]
                self.is_mongo = True
                logger.info(f"Connected to MongoDB Atlas: {settings.DB_NAME}")
            except Exception as e:
                logger.error(f"MongoDB connection failed: {e}. Falling back to SQLite.")
                self._init_sqlite()
        else:
            logger.info("MongoDB URI not configured. Using SQLite database.")
            self._init_sqlite()

    def _init_sqlite(self):
        self.is_mongo = False
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        # Create Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create Messages Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                msg_type TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        # Create Agent State Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_states (
                session_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"SQLite database initialized at: {self.sqlite_path}")

    # --- Sessions API ---

    async def create_session(self, session_id: str, name: str) -> Dict[str, Any]:
        now_str = datetime.now().isoformat()
        
        if self.is_mongo:
            session_doc = {
                "_id": session_id,
                "name": name,
                "created_at": now_str,
                "updated_at": now_str
            }
            await self.db.sessions.insert_one(session_doc)
            return {"id": session_id, "name": name, "created_at": now_str, "updated_at": now_str}
        
        # SQLite
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, name, now_str, now_str)
        )
        conn.commit()
        conn.close()
        return {"id": session_id, "name": name, "created_at": now_str, "updated_at": now_str}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        if self.is_mongo:
            cursor = self.db.sessions.find().sort("updated_at", -1)
            sessions = []
            async for doc in cursor:
                sessions.append({
                    "id": doc["_id"],
                    "name": doc["name"],
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
                })
            return sessions
            
        # SQLite
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        sessions = []
        for r in rows:
            sessions.append({
                "id": r["id"],
                "name": r["name"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"]
            })
        conn.close()
        return sessions

    async def delete_session(self, session_id: str) -> bool:
        if self.is_mongo:
            res_s = await self.db.sessions.delete_one({"_id": session_id})
            await self.db.messages.delete_many({"session_id": session_id})
            await self.db.agent_states.delete_one({"_id": session_id})
            return res_s.deleted_count > 0
            
        # SQLite
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        # SQLite foreign keys must be enabled manually if cascade is needed, or just delete manually
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM agent_states WHERE session_id = ?", (session_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # --- Messages API ---

    async def add_message(
        self, session_id: str, sender: str, content: str, msg_type: str = "text", metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        now_str = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        if self.is_mongo:
            msg_doc = {
                "session_id": session_id,
                "sender": sender,
                "content": content,
                "msg_type": msg_type,
                "metadata": metadata,
                "created_at": now_str
            }
            await self.db.messages.insert_one(msg_doc)
            # Update updated_at in session
            await self.db.sessions.update_one(
                {"_id": session_id},
                {"$set": {"updated_at": now_str}}
            )
            msg_doc["id"] = str(msg_doc["_id"])
            del msg_doc["_id"]
            return msg_doc
            
        # SQLite
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, sender, content, msg_type, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, sender, content, msg_type, metadata_json, now_str)
        )
        msg_id = cursor.lastrowid
        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now_str, session_id))
        conn.commit()
        conn.close()
        
        return {
            "id": msg_id,
            "session_id": session_id,
            "sender": sender,
            "content": content,
            "msg_type": msg_type,
            "metadata": metadata,
            "created_at": now_str
        }

    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        if self.is_mongo:
            cursor = self.db.messages.find({"session_id": session_id}).sort("created_at", 1)
            messages = []
            async for doc in cursor:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                messages.append(doc)
            return messages
            
        # SQLite
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
        rows = cursor.fetchall()
        messages = []
        for r in rows:
            meta = None
            if r["metadata"]:
                try:
                    meta = json.loads(r["metadata"])
                except Exception:
                    pass
            messages.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "sender": r["sender"],
                "content": r["content"],
                "msg_type": r["msg_type"],
                "metadata": meta,
                "created_at": r["created_at"]
            })
        conn.close()
        return messages

    # --- Agent State Checkpointer API ---

    async def save_agent_state(self, session_id: str, state_data: Dict[str, Any]) -> None:
        now_str = datetime.now().isoformat()
        if self.is_mongo:
            await self.db.agent_states.update_one(
                {"_id": session_id},
                {"$set": {"state_data": state_data, "updated_at": now_str}},
                upsert=True
            )
            return

        # SQLite
        state_str = json.dumps(state_data)
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO agent_states (session_id, state_data, updated_at) VALUES (?, ?, ?)",
            (session_id, state_str, now_str)
        )
        conn.commit()
        conn.close()

    async def get_agent_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mongo:
            doc = await self.db.agent_states.find_one({"_id": session_id})
            if doc:
                return doc["state_data"]
            return None

        # SQLite
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT state_data FROM agent_states WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
        return None

db_service = DatabaseService()
