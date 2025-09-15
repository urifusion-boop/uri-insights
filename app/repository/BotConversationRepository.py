from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase


class BotConversationRepository:
    @staticmethod
    async def create_conversation(
        user_id: str, new_messages: list, db: AsyncIOMotorDatabase
    ):
        """
        Append new messages to a user's conversation. Creates the document if it doesn't exist.
        """
        await db["conversations"].update_one(
            {"user_id": user_id},
            {"$push": {"messages": {"$each": new_messages}}},
            upsert=True,
        )

    @staticmethod
    async def get_conversations(user_id: str, db: AsyncIOMotorDatabase) -> Any:
        """
        Retrieve all messages from a user's conversation.
        """
        conversation = await db["conversations"].find_one({"user_id": user_id})
        return conversation.get("messages", []) if conversation else []

    @staticmethod
    async def delete_conversations(user_id: str, db: AsyncIOMotorDatabase) -> bool:
        """
        Delete a user's conversation history.
        """
        result = await db["conversations"].delete_one({"user_id": user_id})
        return result.deleted_count > 0
