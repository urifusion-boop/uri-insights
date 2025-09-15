from app.services.uri_microservices.UriBackendService import UriBackendService


class UserHelper:
    @staticmethod
    async def get_user_email(user_id):
        try:
            user = await UriBackendService.get_user_details(user_id)
            return user.get("email", "")
        except Exception as e:
            raise Exception(f"Error in getting user email: {e}")
