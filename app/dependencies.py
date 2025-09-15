from typing import Generator

from fastapi import HTTPException, Request
from app.core.helpers.middleware_helper import MiddlewareHelper
from app.database import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.middlewares.FeatureLimitMiddleware import FeatureLimitMiddleware


def get_db_dependency() -> Generator[AsyncIOMotorDatabase, None, None]:
    db = get_db()
    try:
        yield db
    finally:
        pass


def get_user_auth_token(request: Request) -> str:
    auth_token = request.headers.get("Authorization")
    if not auth_token:
        raise HTTPException(status_code=401, detail="Auth token is missing")
    return auth_token


async def enforce_feature_limit(request: Request):
    db = get_db()
    user_id = MiddlewareHelper.get_user_id(request)

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not provided in request")

    url_path = await FeatureLimitMiddleware.get_url_path(request.url.path, request)
    print("\nURL Path after formatting:", url_path)
    if not url_path:
        return

    result = await FeatureLimitMiddleware.verify_feature_limit(
        user_id=user_id, url_path=url_path
    )

    payload = await FeatureLimitMiddleware.handle_feature_limit_result(
        db, result, user_id, url_path
    )
    return payload
