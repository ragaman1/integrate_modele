import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongo_uri):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client["telegram_bot_db"]
        self.chats_collection = self.db["chats"]
        self.messages_collection = self.db["messages"]
        self.rate_limit_collection = self.db['rate_limits']  # New collection for rate limiting


    async def create_indexes(self):
        await self.chats_collection.create_index("chat_id", unique=True)
        await self.chats_collection.create_index("username")
        await self.chats_collection.create_index("first_name")
        await self.rate_limit_collection.create_index('reset_time')



        await self.messages_collection.create_index([("chat_id", pymongo.ASCENDING), ("timestamp", pymongo.ASCENDING)])
        await self.messages_collection.create_index("sender")
        await self.messages_collection.create_index([("content", pymongo.TEXT)])

        logger.info("Indexes created on 'chats' and 'messages' collections.")


    # Rate limiting method
    async def check_and_increment_rate_limit(self, user_id: int, current_timestamp: float, max_messages: int, window: int) -> bool:
        """
        Checks if a user has exceeded the rate limit and increments the message count.

        Args:
            user_id (int): The Telegram user ID.
            current_timestamp (float): The current timestamp.
            max_messages (int): Maximum allowed messages within the window.
            window (int): Time window in seconds.

        Returns:
            bool: True if the user is allowed to send the message, False otherwise.
        """
        doc = await self.rate_limit_collection.find_one({'user_id': user_id})
        if doc:
            if current_timestamp > doc['reset_time']:
                # Reset the count and set a new reset time
                await self.rate_limit_collection.update_one(
                    {'user_id': user_id},
                    {'$set': {'count': 1, 'reset_time': current_timestamp + window}}
                )
                return True
            else:
                if doc['count'] < max_messages:
                    # Increment the message count
                    await self.rate_limit_collection.update_one(
                        {'user_id': user_id},
                        {'$inc': {'count': 1}}
                    )
                    return True
                else:
                    # Rate limit exceeded
                    return False
        else:
            # First message from the user
            await self.rate_limit_collection.insert_one({
                'user_id': user_id,
                'count': 1,
                'reset_time': current_timestamp + window
            })
            return True




    async def test_connection(self):
        try:
            server_info = await self.client.admin.command("serverStatus")
            return server_info.get("version", "Unknown")
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            raise

    async def update_chat_metadata(self, chat_id, first_name, username):
        await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"first_name": first_name, "username": username}},
            upsert=True
        )

    async def insert_message(self, chat_id, timestamp, sender, content):
        await self.messages_collection.insert_one({
            "chat_id": chat_id,
            "timestamp": timestamp,
            "sender": sender,
            "content": content
        })

    async def get_chat_history_cleared_at(self, chat_id):
        chat_doc = await self.chats_collection.find_one({"chat_id": chat_id})
        return chat_doc.get("history_cleared_at") if chat_doc else None

    async def clear_chat_history(self, chat_id, current_time):
        await self.chats_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"history_cleared_at": current_time}},
            upsert=True
        )

    async def get_total_words(self, chat_id, history_cleared_at):
        pipeline = [
            {"$match": {"chat_id": chat_id}},
        ]
        
        if history_cleared_at:
            pipeline.append({"$match": {"timestamp": {"$gt": history_cleared_at}}})
        
        pipeline.append({
            "$group": {
                "_id": "$chat_id",
                "total_words": {
                    "$sum": {
                        "$size": {
                            "$split": ["$content", " "]
                        }
                    }
                }
            }
        })
        
        agg_result = await self.messages_collection.aggregate(pipeline).to_list(length=1)
        return agg_result[0]["total_words"] if agg_result else 0

    async def trim_chat_history(self, chat_id, history_cleared_at, max_words):
        total_words = await self.get_total_words(chat_id, history_cleared_at)
        while total_words > max_words:
            query = {"chat_id": chat_id}
            if history_cleared_at:
                query["timestamp"] = {"$gt": history_cleared_at}
            oldest_message = await self.messages_collection.find_one(query, sort=[("timestamp", pymongo.ASCENDING)])
            if not oldest_message:
                break
            await self.messages_collection.delete_one({"_id": oldest_message["_id"]})
            removed_words = len(oldest_message["content"].split())
            total_words -= removed_words
            logger.debug(f"Removed message ID {oldest_message['_id']} with {removed_words} words.")

    async def get_chat_history(self, chat_id, history_cleared_at, max_words):
        query = {"chat_id": chat_id}
        if history_cleared_at:
            query["timestamp"] = {"$gt": history_cleared_at}

        cursor = self.messages_collection.find(query).sort("timestamp", pymongo.ASCENDING)
        all_messages = await cursor.to_list(length=None)

        chat_history = []
        current_word_count = 0
        for msg in all_messages:
            words = msg["content"].split()
            msg_word_count = len(words)
            if current_word_count + msg_word_count > max_words:
                break
            role = "user" if msg["sender"] == "user" else "assistant"
            chat_history.append({"role": role, "content": msg["content"]})
            current_word_count += msg_word_count

        return chat_history

    async def reset_collections(self):
        try:
            await self.chats_collection.drop()
            await self.messages_collection.drop()
            logger.info("Successfully dropped 'chats' and 'messages' collections.")
            
            # Recreate collections and indexes
            await self.create_indexes()
        except Exception as e:
            logger.error(f"Error resetting collections: {e}")
            raise

    async def reset_database(self):
        try:
            await self.client.drop_database("telegram_bot_db")
            logger.info("Successfully dropped the 'telegram_bot_db' database.")
            
            # Re-initialize the database and collections
            self.db = self.client["telegram_bot_db"]
            self.chats_collection = self.db["chats"]
            self.messages_collection = self.db["messages"]
            await self.create_indexes()
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            raise



    # Rate limiting method
    async def check_and_increment_rate_limit(self, user_id: int, current_timestamp: float, max_messages: int, window: int) -> bool:
        """
        Checks if a user has exceeded the rate limit and increments the message count.

        Args:
            user_id (int): The Telegram user ID.
            current_timestamp (float): The current timestamp.
            max_messages (int): Maximum allowed messages within the window.
            window (int): Time window in seconds.

        Returns:
            bool: True if the user is allowed to send the message, False otherwise.
        """
        doc = await self.rate_limit_collection.find_one({'user_id': user_id})
        if doc:
            if current_timestamp > doc['reset_time']:
                # Reset the count and set a new reset time
                await self.rate_limit_collection.update_one(
                    {'user_id': user_id},
                    {'$set': {'count': 1, 'reset_time': current_timestamp + window}}
                )
                return True
            else:
                if doc['count'] < max_messages:
                    # Increment the message count
                    await self.rate_limit_collection.update_one(
                        {'user_id': user_id},
                        {'$inc': {'count': 1}}
                    )
                    return True
                else:
                    # Rate limit exceeded
                    return False
        else:
            # First message from the user
            await self.rate_limit_collection.insert_one({
                'user_id': user_id,
                'count': 1,
                'reset_time': current_timestamp + window
            })
            return True

