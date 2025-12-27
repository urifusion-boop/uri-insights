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
            return result.get("responseData") if result else None
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
        url = f"{UriBackendService.base_url}/trial/usage/increment"
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

    @staticmethod
    async def search_apollo_persons(params: dict):
        """
        Search for people in Apollo using person_titles and organization name.

        Args:
            params: Dictionary containing:
                - person_titles: List of job titles to search for
                - q_organization_name: Organization name
                - page: Page number (default 1)
                - per_page: Results per page (default 3)

        Returns:
            Apollo API response with matched people
        """
        url = "https://api.apollo.io/api/v1/mixed_people/search"

        try:
            # Prepare Apollo API request headers
            headers = {
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": settings.APOLLO_API_KEY
            }

            # Prepare request body
            body = {
                "api_key": settings.APOLLO_API_KEY,
                "person_titles": params.get("person_titles", []),
                "q_organization_name": params.get("q_organization_name", ""),
                "page": params.get("page", 1),
                "per_page": params.get("per_page", 3)
            }

            # Make direct API call to Apollo
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=body, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "responseCode": 200,
                            "responseData": data,
                            "status": True
                        }
                    else:
                        error_text = await response.text()
                        print(f"Apollo API error: {response.status} - {error_text}")
                        return {
                            "responseCode": response.status,
                            "responseMessage": f"Apollo API error: {error_text}",
                            "status": False
                        }
        except Exception as e:
            print(f"Exception occurred searching Apollo persons: {e}")
            import traceback
            traceback.print_exc()
            return {
                "responseCode": 500,
                "responseMessage": str(e),
                "status": False
            }
