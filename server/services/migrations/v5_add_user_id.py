from . import Migration
import sqlite3


class V5AddUserId(Migration):
    version = 5
    description = "Add user_id to canvases and chat_sessions"

    def up(self, conn: sqlite3.Connection) -> None:
        # Add user_id column to canvases
        cursor = conn.execute("PRAGMA table_info(canvases)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'user_id' not in columns:
            conn.execute("ALTER TABLE canvases ADD COLUMN user_id TEXT DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_canvases_user_id ON canvases(user_id)")

        # Add user_id column to chat_sessions
        cursor = conn.execute("PRAGMA table_info(chat_sessions)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'user_id' not in columns:
            conn.execute("ALTER TABLE chat_sessions ADD COLUMN user_id TEXT DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)")

    def down(self, conn: sqlite3.Connection) -> None:
        pass
