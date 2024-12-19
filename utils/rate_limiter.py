# utils/rate_limiter.py

import sqlite3
from datetime import datetime, timedelta
import os
from utils.logging_config import logger

class RateLimiter:
    def __init__(self, max_requests=5, time_window=24):
        self.max_requests = max_requests
        self.time_window = timedelta(hours=time_window)
        # Store the database in the project root directory
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rate_limit.db')
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_requests (
                        user_id INTEGER,
                        timestamp DATETIME,
                        PRIMARY KEY (user_id, timestamp)
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def _cleanup_old_requests(self, user_id):
        try:
            cutoff_time = datetime.now() - self.time_window
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM user_requests 
                    WHERE user_id = ? AND timestamp < ?
                ''', (user_id, cutoff_time))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Cleanup error for user {user_id}: {e}")

    def can_make_request(self, user_id):
        try:
            self._cleanup_old_requests(user_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM user_requests 
                    WHERE user_id = ?
                ''', (user_id,))
                count = cursor.fetchone()[0]

                if count >= self.max_requests:
                    return False

                cursor.execute('''
                    INSERT INTO user_requests (user_id, timestamp)
                    VALUES (?, ?)
                ''', (user_id, datetime.now()))
                conn.commit()
                
                return True
        except sqlite3.Error as e:
            logger.error(f"Error checking request limit for user {user_id}: {e}")
            return False

    def get_remaining_requests(self, user_id):
        try:
            self._cleanup_old_requests(user_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM user_requests 
                    WHERE user_id = ?
                ''', (user_id,))
                count = cursor.fetchone()[0]
                
                return self.max_requests - count
        except sqlite3.Error as e:
            logger.error(f"Error getting remaining requests for user {user_id}: {e}")
            return 0

    def get_oldest_request_time(self, user_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp FROM user_requests 
                    WHERE user_id = ? 
                    ORDER BY timestamp ASC 
                    LIMIT 1
                ''', (user_id,))
                result = cursor.fetchone()
                return datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S.%f') if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting oldest request time for user {user_id}: {e}")
            return None