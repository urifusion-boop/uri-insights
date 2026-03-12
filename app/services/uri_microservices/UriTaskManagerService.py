from datetime import datetime
import traceback
from typing import Tuple
from app.core.config import settings
from app.domain.enums.endpoints_enum import EndpointsEnum, UriTaskManagerEndpointsEnum
from app.domain.enums.microservicestype_enum import MicroServiceTypeEnum
from app.domain.enums.urigatewayendpoints_enum import UriGatewayEndpointsEnum
from app.services.azure.producers.ExceptionLogProducer import (
    ExceptionLogQueueProducerService,
)
from app.services.uri_microservices.UriGatewayService import UriGatewayService


class UriTaskManagerService:
    base_url = UriGatewayEndpointsEnum.TASK_MANAGER.value

    @staticmethod
    async def feature_limit_check(user_id: str, url_path: str):
        if not user_id or not url_path:
            print("User ID or URL path is missing for feature limit check")
            return None
        url = UriTaskManagerService.base_url + settings.URI_TASK_MANAGER_FEATURE_LIMIT
        params = {"userId": user_id, "endpoint": url_path}
        try:
            result = await UriGatewayService.get(url, params=params)
            return result
        except Exception as e:
            print("Exception occurred in checking feature limit: ", e)
            log_data = {
                "userId": user_id,
                "exceptionDate": datetime.utcnow().isoformat() + "Z",
                "method": "POST",
                "status": 500,
                "exception": "".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                ),
                "serviceType": MicroServiceTypeEnum.URI_INSIGHTS.value,
            }
            await ExceptionLogQueueProducerService.publish_exception_log(log_data)
            return None

    @staticmethod
    async def update_user_feature_limit_specific_limit(
        user_id: str, url_path: str, count: int
    ):
        if not user_id or not url_path:
            print("❌ [UriTaskManagerService] User ID or URL path is missing for updating feature limit")
            return None
        url = (
            UriTaskManagerService.base_url
            + settings.URI_TASK_MANAGER_UPDATE_FEATURE_LIMIT_SPECIFIC_LIMIT
        )
        request_body = {"userId": user_id, "urlPath": url_path, "count": count}
        print(f"🔄 [UriTaskManagerService] Calling task-manager: {url}")
        print(f"📦 [UriTaskManagerService] Request body: {request_body}")
        try:
            result = await UriGatewayService.put(url, request_body)
            print(f"✅ [UriTaskManagerService] Task-manager response: {result}")
            return result
        except Exception as e:
            print(f"❌ [UriTaskManagerService] Exception occurred in updating specific feature limit: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    async def update_user_feature_limit(update_data: dict):
        url = (
            UriTaskManagerService.base_url
            + settings.URI_TASK_MANAGER_UPDATE_FEATURE_LIMIT_OBJECT
        )
        try:
            result = await UriGatewayService.put(url, update_data)
            return result
        except Exception as e:
            print("Exception occurred in updating feature limit object: ", e)
            return None

    @staticmethod
    async def create_user_feature_limit(user_id: str, user_email: str):
        url = (
            UriTaskManagerService.base_url
            + settings.URI_TASK_MANAGER_CREATE_FEATURE_LIMIT
        )
        request_body = {"userId": user_id, "email": user_email}

        try:
            result = await UriGatewayService.post(url, data=request_body)
            return result
        except Exception as e:
            print("Exception occurred in creating feature limit: ", e)
            return None

    @staticmethod
    async def get_user_feature_limit(user_id: str):
        if not user_id:
            print("User ID is missing for getting feature limit")
            return None
        url = (
            UriTaskManagerService.base_url
            + UriTaskManagerEndpointsEnum.GET_FEATURE_LIMIT.value
            + f"/{user_id}"
        )
        try:
            result = await UriGatewayService.get(url, max_retries=1)
            return result
        except Exception as e:
            print("Exception occurred in getting feature limit: ", e)
            return None

    @staticmethod
    async def get_elapsed_leads_limit_and_count(user_id) -> Tuple[int, int]:
        feature_limit = (
            await UriTaskManagerService.feature_limit_check(
                user_id, EndpointsEnum.LEAD_GEN.value
            )
        ).get("responseData", {})
        limit_available = feature_limit.get("limitAvailable", 0)
        current_count = (
            feature_limit.get("data", {})
            .get("lead", {})
            .get("noOfLeads", 0)
            .get("count", 0)
        )

        return limit_available, current_count

    @staticmethod
    async def check_payment_balance(
        user_id: str,
        action_type: str,
        payment_mode: str,
        quantity: int = 1
    ):
        """
        Check if user has sufficient balance (wallet or credits) for a specific action

        Args:
            user_id: User ID to check
            action_type: Type of action (e.g., "SALES_SIGNAL_SCAN", "ENRICHMENT_EMAIL", "ENRICHMENT_PHONE")
            payment_mode: "WALLET" or "CREDITS"
            quantity: Number of actions (default: 1)

        Returns:
            Response with balance information and hasSufficientBalance flag
        """
        if not user_id or not action_type or not payment_mode:
            print("Missing required parameters for balance check")
            return None

        url = UriTaskManagerService.base_url + "/payment-gating/check-balance"
        params = {
            "userId": user_id,
            "actionType": action_type,
            "paymentMode": payment_mode,
            "quantity": quantity
        }

        try:
            result = await UriGatewayService.get(url, params=params)
            return result
        except Exception as e:
            print(f"❌ Exception occurred in checking balance: {str(e)}")
            return None

    @staticmethod
    async def deduct_payment(
        user_id: str,
        action_type: str,
        payment_mode: str,
        quantity: int = 1,
        reference: str = None,
        narration: str = None
    ):
        """
        Deduct payment from user's wallet or credits for a specific action

        Args:
            user_id: User ID to deduct from
            action_type: Type of action (e.g., "SALES_SIGNAL_SCAN", "SALES_SIGNAL_VERIFIED", "ENRICHMENT_EMAIL", "ENRICHMENT_PHONE")
            payment_mode: "WALLET" or "CREDITS"
            quantity: Number of actions (default: 1)
            reference: Optional transaction reference
            narration: Optional transaction description

        Returns:
            Response from payment gating service
        """
        if not user_id or not action_type or not payment_mode:
            print("Missing required parameters for payment deduction")
            return None

        url = UriTaskManagerService.base_url + "/payment-gating/deduct"

        request_body = {
            "userId": user_id,
            "actionType": action_type,
            "paymentMode": payment_mode,
            "quantity": quantity
        }

        if reference:
            request_body["reference"] = reference

        if narration:
            request_body["narration"] = narration

        try:
            result = await UriGatewayService.post(url, data=request_body)
            print(f"✅ Payment deduction result: {result}")
            return result
        except Exception as e:
            print(f"❌ Exception occurred in deducting payment: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
