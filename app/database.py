from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from urllib.parse import quote_plus
from app.core.config import settings

client: AsyncIOMotorClient | None = None


def connect_to_mongo(database_name: str) -> None:
    global client

    if settings.DEV_ENV == "Development":
        # Check if username and password are provided
        if settings.MONGODB_USER and settings.MONGODB_PASSWORD:
            user = quote_plus(settings.MONGODB_USER)
            password = quote_plus(settings.MONGODB_PASSWORD)
            host = settings.MONGODB_HOST
            uri = f"mongodb://{user}:{password}@{host}/{database_name}"
            print(f"Generated URI: {uri.replace(password, '*****')}")
        else:
            # Local MongoDB without authentication
            uri = settings.MONGODB_URI
            print(f"Generated URI: {uri}")
        client = AsyncIOMotorClient(uri)
    else:
        client = AsyncIOMotorClient(settings.MONGODB_URI)


def get_db() -> AsyncIOMotorDatabase:
    if client is None:
        raise ConnectionError("Client is not connected.")
    return client.get_default_database()


def get_backend_db() -> AsyncIOMotorDatabase:
    """Get connection to uri-backend database (Uri) for user lookups"""
    if client is None:
        raise ConnectionError("Client is not connected.")
    return client["Uri"]
