from app.core.config import settings
from app.domain.enums.urigatewayendpoints_enum import UriGatewayEndpointsEnum
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
