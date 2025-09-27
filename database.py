import sqlite3
import datetime
from typing import List, Tuple, Optional, Dict, Any

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица фильмов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    code TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    caption TEXT,
                    added_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица каналов (для обязательной подписки)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    title TEXT
                )
            ''')
            
            conn.commit()

    # Методы для работы с фильмами
    def add_movie(self, code: str, file_id: str, caption: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO movies (code, file_id, caption) VALUES (?, ?, ?)',
                (code, file_id, caption)
            )
            conn.commit()

    def get_movie(self, code: str) -> Optional[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT code, file_id, caption FROM movies WHERE code = ?', (code,))
            return cursor.fetchone()

    def delete_movie(self, code: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM movies WHERE code = ?', (code,))
            conn.commit()

    def get_all_movies(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT code, file_id, caption FROM movies ORDER BY code')
            return cursor.fetchall()

    def get_movies_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM movies')
            return cursor.fetchone()[0]

    # Методы для работы с пользователями
    def add_user(self, user_id: int, username: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            conn.commit()

    def update_user_activity(self, user_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_activity = ? WHERE user_id = ?',
                (datetime.datetime.now(), user_id)
            )
            conn.commit()

    def get_user(self, user_id: int) -> Optional[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, joined_at FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()

    def get_users_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]

    def get_all_users(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username FROM users')
            return cursor.fetchall()

    # Методы для работы с каналами
    def add_channel(self, channel_id: int, username: str, title: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO channels (channel_id, username, title) VALUES (?, ?, ?)',
                (channel_id, username, title)
            )
            conn.commit()

    def get_channel(self, channel_id: int) -> Optional[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT channel_id, username, title FROM channels WHERE channel_id = ?', (channel_id,))
            return cursor.fetchone()

    def get_all_channels(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT channel_id, username, title FROM channels')
            return cursor.fetchall()

    def delete_channel(self, channel_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
            conn.commit()

    def get_popular_codes(self, limit: int = 10) -> List[Tuple]:
        # В будущем можно добавить счетчик запросов для каждого фильма
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT code FROM movies ORDER BY added_date DESC LIMIT ?', (limit,))
            return cursor.fetchall()