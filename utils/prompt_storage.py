# utils/prompt_storage.py

import aiosqlite
from datetime import datetime
import os
from typing import List
from utils.logging_config import logger

class PromptStorage:
    def __init__(self, db_path: str = None, max_prompts: int = 5):
        """
        Initialize the PromptStorage with the path to the database and maximum prompts to store.
        """
        self.max_prompts = max_prompts
        # If no db_path provided, default to 'rate_limit.db' in project root
        if db_path is None:
            self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rate_limit.db')
        else:
            self.db_path = db_path

    async def _init_db(self):
        """
        Initialize the database table for storing user prompts.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS user_prompts (
                        user_id INTEGER,
                        timestamp DATETIME,
                        prompt TEXT,
                        PRIMARY KEY (user_id, timestamp)
                    )
                ''')
                await db.commit()
                logger.info("Prompt storage table ensured.")
        except Exception as e:
            logger.error(f"Database initialization error in PromptStorage: {e}")
            raise

    async def add_prompt(self, user_id: int, prompt: str):
        """
        Add a new prompt for a user and ensure only the last `max_prompts` are stored.
        """
        try:
            # Ensure database is initialized
            await self._init_db()
            
            timestamp = datetime.now()
            async with aiosqlite.connect(self.db_path) as db:
                # Insert the new prompt
                await db.execute('''
                    INSERT INTO user_prompts (user_id, timestamp, prompt)
                    VALUES (?, ?, ?)
                ''', (user_id, timestamp, prompt))
                await db.commit()
                logger.info(f"Added prompt for user {user_id} at {timestamp}.")

                # Delete oldest prompts if exceeding max_prompts
                await db.execute('''
                    DELETE FROM user_prompts 
                    WHERE user_id = ? AND timestamp NOT IN (
                        SELECT timestamp FROM user_prompts
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                ''', (user_id, user_id, self.max_prompts))
                await db.commit()
                logger.info(f"Ensured only last {self.max_prompts} prompts are stored for user {user_id}.")
        except Exception as e:
            logger.error(f"Error adding prompt for user {user_id}: {e}")
            raise

    async def get_last_prompts(self, user_id: int) -> List[str]:
        """
        Retrieve the last `max_prompts` prompts for a user.
        """
        try:
            # Ensure database is initialized
            await self._init_db()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT prompt FROM user_prompts
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (user_id, self.max_prompts)) as cursor:
                    rows = await cursor.fetchall()
                    prompts = [row[0] for row in rows]
                    logger.info(f"Retrieved {len(prompts)} prompts for user {user_id}.")
                    return prompts
        except Exception as e:
            logger.error(f"Error retrieving prompts for user {user_id}: {e}")
            return []

    async def clear_prompts(self, user_id: int):
        """
        Clear all prompts for a specific user.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM user_prompts WHERE user_id = ?', (user_id,))
                await db.commit()
                logger.info(f"Cleared all prompts for user {user_id}.")
        except Exception as e:
            logger.error(f"Error clearing prompts for user {user_id}: {e}")
            raise