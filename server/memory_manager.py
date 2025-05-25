import sqlite3
import os
import threading

class MemoryManager:
    def __init__(self, db_path="memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)        
        self.lock = threading.Lock()
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_summarized INTEGER DEFAULT 0,
                    is_history INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def add_message(self, role, content, is_history=False):
        with self.lock:
            with self.conn:
                self.conn.execute(
                    'INSERT INTO memory (role, content, is_history) VALUES (?, ?, ?)',
                    (role, content, int(is_history))
                )

    def get_recent_memories(self, limit=5):
        with self.lock:
            with self.conn:
                cursor = self.conn.execute('SELECT role, content FROM memory ORDER BY id DESC LIMIT ?', (limit,))
                return cursor.fetchall()

    def get_unsummarized(self, limit=5):
        with self.lock:
            with self.conn:
                cursor = self.conn.execute(
                    'SELECT id, role, content FROM memory WHERE is_summarized = 0 AND is_history = 0 ORDER BY id ASC LIMIT ?',
                    (limit,)
                )
                rows = cursor.fetchall()
                return [{"id": row[0], "role": row[1], "content": row[2]} for row in rows]

    def add_summary(self, summary):
        with self.lock:
            with self.conn:
                self.conn.execute(
                    'INSERT INTO memory (role, content, is_summarized, is_history) VALUES (?, ?, 1, 0)',
                    ("summary", summary)
                )

    def mark_as_summarized(self, ids):
        with self.lock:
            if not ids:
                return
            placeholders = ','.join(['?'] * len(ids))
            with self.conn:
                self.conn.execute(f'UPDATE memory SET is_summarized = 1 WHERE id IN ({placeholders})', ids)

    def get_unsummarized_history(self, limit=5):
        with self.lock:
            with self.conn:
                cursor = self.conn.execute(
                    'SELECT id, role, content FROM memory WHERE is_summarized = 0 AND is_history = 1 ORDER BY id ASC LIMIT ?',
                    (limit,)
                )
                rows = cursor.fetchall()
                return [{"id": row[0], "role": row[1], "content": row[2]} for row in rows]

    def get_latest_history_summary(self):
        with self.lock:
            with self.conn:
                cursor = self.conn.execute('''
                    SELECT content FROM memory
                    WHERE is_history = 1 AND is_summarized = 1
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''')
                row = cursor.fetchone()
                return row[0] if row else ""

    def add_history_summary(self, summary):
        with self.lock:
            with self.conn:
                self.conn.execute(
                    'INSERT INTO memory (role, content, is_summarized, is_history) VALUES (?, ?, 1, 1)',
                    ("summary", summary)
                )

    def clear_memory(self):
        with self.lock:
            with self.conn:
                self.conn.execute('DELETE FROM memory')

    def close(self):
        self.conn.close()