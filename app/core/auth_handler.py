# app/core/auth_handler.py

import time
import jwt
from typing import Dict, Any
from fastapi import HTTPException, Header
from app.core.config import settings

SECRET_KEY = settings.AUTHJWT_SECRET_KEY
ALGORITHM = "HS256"


def decode_jwt(token: str) -> Any:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if decoded_token["exp"] < time.time():
            raise HTTPException(status_code=403, detail="Token expired.")
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid token.")
    except Exception as e:
        raise HTTPException(status_code=403, detail="Token validation error: " + str(e))


def get_meta_access_token(meta_access_token: str = Header(None)):
    if not meta_access_token:
        raise HTTPException(status_code=400, detail="Meta-Access-Token header missing")
    return meta_access_token


def get_tiktok_access_token(tiktok_access_token: str = Header(None)):
    if not tiktok_access_token:
        raise HTTPException(
            status_code=400, detail="Tiktok-Access-Token header missing"
        )
    return tiktok_access_token


def get_x_access_token(x_access_token: str = Header(None)):
    if not x_access_token:
        raise HTTPException(status_code=400, detail="X-Access-Token header missing")
    return x_access_token


def get_linkedin_access_token(linkedin_access_token: str = Header(None)):
    if not linkedin_access_token:
        raise HTTPException(
            status_code=400, detail="Linkedin-Access-Token header missing"
        )
    return linkedin_access_token
