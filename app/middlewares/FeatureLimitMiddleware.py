import json
from fastapi import HTTPException, Request
from app.core.config import settings
from app.core.helpers.featurelimit_helper import FeatureLimitHelper
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.enums.tracker_enum import TrackerTypeEnum
from app.services.uri_microservices.UriBackendService import UriBackendService
from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService
from motor.motor_asyncio import AsyncIOMotorDatabase


class FeatureLimitExceeded(Exception):
    """Custom exception for feature limit exceeded errors."""

    def __init__(self, message: str = "Feature limit exceeded."):
        super().__init__(message)
        self.message = message


class FeatureLimitMiddleware:
    feature_limit_check_url = settings.URI_TASK_MANAGER_FEATURE_LIMIT
    mutation_endpoints = [
        EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value,
        EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value,
    ]
    value_error_message = "Error occurred in verifying your access to this feature."

    # --- Private helpers and methods ---
    @staticmethod
    def __generate_error_message(limit_check_result: dict, endpoint: str) -> str:
        feature_limit_object = FeatureLimitMiddleware.__get_limit_data(
            limit_check_result, endpoint
        )
        if feature_limit_object.get("locked"):
            return "This feature is not available for your subscription."
        return "You have reached the quota for your subscription."

    @staticmethod
    def __get_limit_data(feature_limit_check_data: dict, endpoint: str) -> dict:
        feature_name = FeatureLimitHelper.endpoint_to_feature_name_map.get(endpoint, "")
        if not feature_name:
            print("Unsupported endpoint name provided for feature limit check")
            raise ValueError(FeatureLimitMiddleware.value_error_message)

        if feature_name in FeatureLimitHelper.account_tracking_sub_features:
            feature_limit_object = feature_limit_check_data.get(
                "accountTracking", {}
            ).get(feature_name, {})
        else:
            feature_limit_object = feature_limit_check_data.get(feature_name, {})
        return feature_limit_object

    @staticmethod
    def __mutate_payload_for_saving_linkedin_account(limit_check_result: dict) -> dict:
        user_limits = limit_check_result.get("data", {})
        accounts_limit_details = user_limits.get("accountTracking", {}).get(
            "accounts", {}
        )
        available_linkedin_limit = limit_check_result.get("limitAvailable", 0)
        available_account_limit = accounts_limit_details.get(
            "limit", 0
        ) - accounts_limit_details.get("count", 0)
        return min(available_account_limit, available_linkedin_limit)

    @staticmethod
    def __mutate_payload_for_saving_ig_accounts(limit_check_result: dict) -> dict:
        user_limits = limit_check_result.get("data", {})
        if not user_limits:
            print("Empty user limit data for ig account payload mutation")
            raise ValueError(FeatureLimitMiddleware.value_error_message)
        instagram_accounts_limit_details = user_limits.get("accountTracking", {}).get(
            "instagramAccounts", {}
        )
        facebook_accounts_limit_details = user_limits.get("accountTracking", {}).get(
            "facebookAccounts", {}
        )
        accounts_limit_details = user_limits.get("accountTracking", {}).get(
            "accounts", {}
        )
        instagram_accounts_limit = instagram_accounts_limit_details.get("limit")
        instagram_accounts_count = instagram_accounts_limit_details.get("count")
        facebook_accounts_limit = facebook_accounts_limit_details.get("limit")
        facebook_accounts_count = facebook_accounts_limit_details.get("count")

        instagram_limit = (
            0
            if instagram_accounts_limit < instagram_accounts_count
            else (instagram_accounts_limit - instagram_accounts_count)
        )
        facebook_limit = (
            0
            if facebook_accounts_limit < facebook_accounts_count
            else (facebook_accounts_limit - facebook_accounts_count)
        )
        accounts_limits = {
            "instagram_limit": instagram_limit,
            "facebook_limit": facebook_limit,
            "accounts_limit": (
                accounts_limit_details.get("limit", 0)
                - accounts_limit_details.get("count", 0)
            ),
        }

        return accounts_limits

    @staticmethod
    def __get_keyword_tracker_endpoint(request_data: dict) -> str:
        tracker_type = request_data.get("tracker_type")
        if tracker_type == TrackerTypeEnum.KEYWORD.value:
            return EndpointsEnum.KEYWORD_TRACKIING.value
        else:
            return EndpointsEnum.HASHTAG_TRACKING.value

    @staticmethod
    async def __secondary_check(
        db: AsyncIOMotorDatabase,
        user_id: str,
        feature_limit_check_data: dict,
        endpoint: str,
    ) -> bool:
        feature_limit_object = FeatureLimitMiddleware.__get_limit_data(
            feature_limit_check_data, endpoint
        )
        if not feature_limit_object:
            print("Feature limit object not found in secondary check")
            raise ValueError(FeatureLimitMiddleware.value_error_message)
        limit_count = feature_limit_object.get("limit")
        feature_name = FeatureLimitHelper.endpoint_to_feature_name_map.get(endpoint, "")
        print("LIMIT COUNT", limit_count)
        if limit_count == 0:
            return True

        usage_count_dict = await FeatureLimitHelper.get_usage_counts(
            db=db, user_id=user_id, endpoints=[endpoint]
        )
        usage_count = usage_count_dict.get(feature_name, 0)

        return limit_count > usage_count

    # --- Public Methods ----
    @staticmethod
    async def get_url_path(url_path: str, request: Request):
        if url_path == EndpointsEnum.KEYWORD_TRACKIING.value:
            # Read and cache the body
            body_bytes = await request.body()
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                body = {}

            # Save for reuse in route handler
            request._body = body_bytes  # Cache raw body
            url_path = FeatureLimitMiddleware.__get_keyword_tracker_endpoint(body)
        elif (
            url_path == EndpointsEnum.ACCOUNT_TRACKING_REPORT_GEN.value
            or url_path == EndpointsEnum.HASHTAG_TRACKING_REPORT_GEN.value
        ):
            return EndpointsEnum.REPORT_GEN.value
        elif url_path == EndpointsEnum.LEAD_ENRICHMENT.value:
            return FeatureLimitHelper.format_lead_enrichment_url(request)
        return url_path

    @staticmethod
    async def verify_feature_limit(user_id: str, url_path: str):
        if url_path == EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value:
            response = await UriTaskManagerService.feature_limit_check(
                user_id, EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value
            )
            if response:
                result = response.get("responseData", {})
                if result.get("status"):
                    return result
        if url_path == EndpointsEnum.CREATE_INFLUENCER.value:
            url_path = EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value
        result = await UriTaskManagerService.feature_limit_check(user_id, url_path)
        if not result:
            print("Feature limit verification failed")
            return None
        return result.get("responseData", {})

    @staticmethod
    async def handle_feature_limit_result(
        db: AsyncIOMotorDatabase,
        result: dict,
        user_id: str,
        url_path: str,
    ):
        if not result:
            raise HTTPException(status_code=500, detail="Feature limit check failed")

        limit_check_status = result.get("status")
        limit_check_data = result.get("data", {})

        if not limit_check_status and not limit_check_data:
            # Handle missing feature limit
            await FeatureLimitMiddleware.handle_missing_feature_limit_for_user(
                db, user_id
            )

            # Retry feature limit verification after handling
            result = await FeatureLimitMiddleware.verify_feature_limit(
                user_id=user_id, url_path=url_path
            )

            return await FeatureLimitMiddleware.handle_feature_limit_result(
                db, result, user_id, url_path
            )
        error_message = FeatureLimitMiddleware.__generate_error_message(
            limit_check_data, url_path
        )
        if not limit_check_status and limit_check_data:
            raise FeatureLimitExceeded(error_message)
        elif limit_check_status and limit_check_data:
            if await FeatureLimitMiddleware.__secondary_check(
                db=db,
                user_id=user_id,
                feature_limit_check_data=limit_check_data,
                endpoint=url_path,
            ):
                if FeatureLimitMiddleware.should_mutate_payload(url_path):
                    return FeatureLimitMiddleware.mutate_payload(url_path, result)
                return None
            else:
                await FeatureLimitMiddleware.sync_user_feature_limit(
                    db=db,
                    user_id=user_id,
                    limit_id=limit_check_data.get("limitId"),
                )
                raise FeatureLimitExceeded(error_message)
        else:
            print("Feature limit check result:", result)
            raise Exception("Feature limit check failed for unknown reason")

    @staticmethod
    async def handle_missing_feature_limit_for_user(
        db: AsyncIOMotorDatabase, user_id: str
    ):
        # Get user details
        user_details = await UriBackendService.get_user_details(user_id)
        if not user_details:
            print(f"Failed to get details for user with ID {user_id}")
            raise ValueError(FeatureLimitMiddleware.value_error_message)

        # Extract paystack ID
        user_email = user_details.get("email", "")

        if not user_email:
            print(f"User with ID {user_id} has no email")
            raise ValueError(FeatureLimitMiddleware.value_error_message)
        # Send request to task manager to create the user feature limit object
        create_user_limit_response = (
            await UriTaskManagerService.create_user_feature_limit(user_id, user_email)
        )
        if not create_user_limit_response or not create_user_limit_response.get(
            "status"
        ):
            print(f"Error creating user limit object for user with ID {user_id}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to create user limit object for user with ID {user_id} on task manager microservice",
            )

        created_user_limit = create_user_limit_response.get("responseData", {})
        limit_id = created_user_limit.get("limitId")

        # Update user feature limit object with the most current usage counts
        await FeatureLimitMiddleware.sync_user_feature_limit(
            db=db, user_id=user_id, limit_id=limit_id
        )

    @staticmethod
    def should_mutate_payload(url_path: str):
        return url_path in FeatureLimitMiddleware.mutation_endpoints

    @staticmethod
    def mutate_payload(url_path: str, limit_check_result: dict) -> dict:
        payload_mutation_mini_factory = {
            EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value: FeatureLimitMiddleware.__mutate_payload_for_saving_linkedin_account,
            EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value: FeatureLimitMiddleware.__mutate_payload_for_saving_ig_accounts,
        }
        payload_mutation_func = payload_mutation_mini_factory.get(url_path)

        if not payload_mutation_func:
            print("Unsupported url path for mutation")
            raise ValueError(FeatureLimitMiddleware.value_error_message)

        return payload_mutation_func(limit_check_result)

    @staticmethod
    async def sync_user_feature_limit(
        db: AsyncIOMotorDatabase, user_id: str, limit_id: str
    ):
        update_data = await FeatureLimitHelper.construct_feature_limit_update_payload(
            db, limit_id, user_id
        )

        if update_data:
            try:
                updated_feature_limit = (
                    await UriTaskManagerService.update_user_feature_limit(update_data)
                )
                print("Updated feature limit object: ", updated_feature_limit)
            except HTTPException:
                raise
            except Exception as e:
                print(
                    "Exception in updating user feature limit objects with current feature usage counts: ",
                    e,
                )
                raise
        else:
            print("Update data not constructed successfully for user feature limit")
