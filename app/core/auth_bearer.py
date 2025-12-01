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
                await self.validate_subscription(payload)
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

    async def validate_subscription(self, payload: dict):
        # Access the claims from the payload
        claims = payload.get("claims", {})
        user_id = claims.get("userId")

        # Get subscription status and trial status from JWT claims
        subscription_status = claims.get(
            "subscriptionStatus", SubscriptionStatusEnum.INACTIVE
        )
        trial_status_jwt = claims.get("trialStatus", "not_started")

        print(f"🔐 AUTH CHECK - User: {user_id}")
        print(f"   JWT trialStatus: {trial_status_jwt}")
        print(f"   JWT subscriptionStatus: {subscription_status}")

        # If JWT says trial not active, check MongoDB for latest status
        # (handles case where user activated trial after getting JWT)
        trial_status = trial_status_jwt
        if trial_status_jwt != "active" and user_id:
            try:
                print(f"   ⚠ Fetching latest trial status from backend...")
                # Fetch from MongoDB via uri-backend
                from app.services.uri_microservices.UriBackendService import UriBackendService
                result = await UriBackendService.get_trial_status(user_id)
                print(f"   Backend response: {result}")

                if result and result.get("responseData"):
                    # Backend returns: responseData: { "status": "active", ... }
                    trial_status = result["responseData"].get("status", "not_started")
                    print(f"   ✓ Backend trial status: {trial_status}")
                else:
                    print(f"   ✗ Backend returned null or no responseData")
                    trial_status = "not_started"
            except Exception as e:
                # On error, trust JWT claim
                print(f"   ✗ Exception fetching trial status: {e}")
                import traceback
                traceback.print_exc()
                trial_status = trial_status_jwt

        # Allow access if user has active subscription OR active trial
        has_active_subscription = subscription_status == SubscriptionStatusEnum.ACTIVE
        has_active_trial = trial_status == "active"

        print(f"   Final trial_status: {trial_status}")
        print(f"   has_active_subscription: {has_active_subscription}")
        print(f"   has_active_trial: {has_active_trial}")

        if not (has_active_subscription or has_active_trial):
            print(f"   ❌ ACCESS DENIED - No active subscription or trial")
            raise HTTPException(
                status_code=402,
                detail={
                    "status": False,
                    "responseCode": 402,
                    "responseMessage": "Payment required for premium access.",
                    "responseData": {
                        "subscriptionStatus": subscription_status
                        or SubscriptionStatusEnum.INACTIVE,
                        "trialStatus": trial_status
                    },
                },
            )

        print(f"   ✅ ACCESS GRANTED")
