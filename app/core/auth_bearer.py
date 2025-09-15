from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_db
from app.domain.enums.subscription_enum import SubscriptionStatusEnum
from app.repository.CacheRepository import CacheRepository
from .auth_handler import decode_jwt  # Assume decode_jwt extracts claims from the token


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True, validate_subscription: bool = False):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.validate_subscription_flag = validate_subscription

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)
        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            payload = self.verify_jwt(credentials.credentials)
            if not payload:
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token."
                )
            if self.validate_subscription_flag:
                self.validate_subscription(payload)
            # Return the payload so it can be used in routes if necessary
            return payload
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> Optional[dict]:
        try:
            payload = decode_jwt(jwtoken)  # Decode and extract claims
            return payload
        except Exception as e:
            print(f"Error verifying JWT: {e}")
            return None

    def validate_subscription(self, payload: dict):
        # Access the claims from the payload
        claims = payload.get("claims", {})

        # Retrieve subscriptionStatus from claims
        subscription_status = claims.get(
            "subscriptionStatus", SubscriptionStatusEnum.INACTIVE
        )

        if subscription_status != SubscriptionStatusEnum.ACTIVE:
            raise HTTPException(
                status_code=402,
                detail={
                    "status": False,
                    "responseCode": 402,
                    "responseMessage": "Payment required for premium access.",
                    "responseData": {
                        "subscriptionStatus": subscription_status
                        or SubscriptionStatusEnum.INACTIVE
                    },
                },
            )
