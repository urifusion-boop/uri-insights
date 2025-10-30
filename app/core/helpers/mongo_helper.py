from typing import List, Any
from motor.motor_asyncio import AsyncIOMotorCursor


class MongoHelper:
    @staticmethod
    async def paginate_cursor(
        cursor: AsyncIOMotorCursor,
        skip: int = 0,
        limit: int = 50
    ) -> List[Any]:
        """Helper method to paginate a MongoDB cursor."""
        results = []
        cursor = cursor.skip(skip).limit(limit)
        
        async for document in cursor:
            results.append(document)
            
        return results