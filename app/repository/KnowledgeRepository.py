from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app import schemas


class KnowledgeRepository:
    @staticmethod
    async def create_knowledge(
        db: AsyncIOMotorDatabase, knowledge: schemas.KnowledgeCreate
    ) -> Dict[str, Any]:
        db_knowledge = {
            "title": "app-knowledge",
            "content": knowledge.content,
        }
        result = await db["knowledges"].insert_one(db_knowledge)
        db_knowledge["_id"] = result.inserted_id
        return db_knowledge

    @staticmethod
    async def query_knowledge(
        query: str, db: AsyncIOMotorDatabase
    ) -> List[Dict[str, Any]]:
        cursor = db["knowledges"].find({"$text": {"$search": query}})
        results = await cursor.to_list(length=None)  # Convert cursor to list
        return results
