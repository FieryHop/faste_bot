import sqlite3
import json
from datetime import datetime


class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            chat_title TEXT,
            context_messages TEXT NOT NULL,
            detected_topic TEXT,
            sentiment TEXT,
            bot_response TEXT,
            response_generated BOOLEAN NOT NULL,
            participants_count INTEGER
        )
        """)
        self.conn.commit()

    def save_interaction(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO chat_interactions (
            timestamp,
            chat_id,
            chat_title,
            context_messages,
            detected_topic,
            sentiment,
            bot_response,
            response_generated,
            participants_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["timestamp"],
            data["chat_id"],
            data["chat_title"],
            json.dumps(data["context_messages"], ensure_ascii=False),
            data["detected_topic"],
            data["sentiment"],
            data["bot_response"],
            int(data["response_generated"]),
            data["participants_count"]
        ))
        self.conn.commit()

    def get_recent_interactions(self, limit=5):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chat_interactions ORDER BY timestamp DESC LIMIT ?", (limit,))
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()