from fastapi import HTTPException, Request
from app.core.auth_handler import decode_jwt


class MiddlewareHelper:
    @staticmethod
    def get_user_id(request: Request) -> str:
        """
        Extracts the user ID from the JWT in the Authorization header.
        Throws HTTP 403 if missing, invalid, or malformed.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=403, detail="Authorization header missing or malformed"
            )

        token = auth_header.split(" ")[1]
        try:
            payload = decode_jwt(token)
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid or expired token")

        user_id = payload.get("claims", {}).get("userId")
        if not user_id:
            raise HTTPException(status_code=403, detail="User ID not found in token")

        return user_id
