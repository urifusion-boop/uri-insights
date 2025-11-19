import logging
from app.services.uri_microservices.UriBackendService import UriBackendService

logger = logging.getLogger(__name__)


class UserHelper:
    @staticmethod
    async def get_user_email(user_id):
        try:
            user = await UriBackendService.get_user_details(user_id)
            if user is None:
                logger.warning(f"User not found for user_id: {user_id}")
                return ""
            return user.get("email", "")
        except Exception as e:
            # Log error but don't crash - notification is non-critical
            logger.error(f"Failed to fetch user email for user_id {user_id}: {str(e)}")
            return ""
