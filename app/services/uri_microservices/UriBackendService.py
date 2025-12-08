from app.core.config import settings
from app.domain.enums.urigatewayendpoints_enum import UriGatewayEndpointsEnum
from app.domain.enums.endpoints_enum import UriBackendEndpointsEnum
from app.services.uri_microservices.UriGatewayService import UriGatewayService


class UriBackendService:
    base_url = UriGatewayEndpointsEnum.URI_BACKEND.value

    @staticmethod
    async def get_user_details(user_id: str):
        url = UriBackendService.base_url + settings.URI_BACKEND_USER_DETAILS + user_id
        try:
            result = await UriGatewayService.get(url)
            return result.get("responseData")
        except Exception as e:
            print("Exception occurred in checking feature limit: ", e)
            return None

    @staticmethod
    async def get_trial_status(user_id: str):
        """Get trial status from uri-backend"""
        url = f"{UriBackendService.base_url}/trial/status/{user_id}"
        try:
            result = await UriGatewayService.get(url)
            return result
        except Exception as e:
            print(f"Exception occurred getting trial status: {e}")
            return None

    @staticmethod
    async def increment_trial_usage(user_id: str, field: str, amount: int = 1):
        """
        Increment trial usage counter for user.

        Args:
            user_id: User ID
            field: Field to increment (trialLeadsGenerated, trialSignalsUsed, etc.)
            amount: Amount to increment by (default 1)
        """
        url = (
            UriBackendService.base_url
            + UriBackendEndpointsEnum.TRIAL_USAGE_INCREMENT.value
        )
        payload = {
            "userId": user_id,
            "field": field,
            "amount": amount
        }
        try:
            result = await UriGatewayService.post(url, payload)
            return result
        except Exception as e:
            print(f"Exception occurred incrementing trial usage for {field}: ", e)
            return None
