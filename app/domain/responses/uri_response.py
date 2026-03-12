from fastapi import HTTPException
from starlette.responses import JSONResponse
from typing import Any, Dict, Optional, List
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from app.domain.models.chat_model import BaseModel


class UriResponse:
    @staticmethod
    def set_header_data(response: JSONResponse, key: str, data: Any):
        if key and data:
            response.headers[key] = str(data)

    @staticmethod
    def get_status_response(response: Any, status_code: int = HTTP_200_OK):
        # Ensure response is serializable
        if isinstance(response, BaseModel):
            response = response.dict()
        return JSONResponse(status_code=status_code, content=response)

    @staticmethod
    def create_response(
        entity_name: str, data: Any = None, message: Optional[str] = None
    ) -> Dict[str, Any]:
        if data or (data is not None and data.get("status_code", 0) in [200, 201]):
            return {
                "status": True,
                "responseCode": HTTP_201_CREATED,
                "responseMessage": message or f"{entity_name} successfully created.",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_400_BAD_REQUEST,
                "responseMessage": f"Failed to create {entity_name}.",
            }

    @staticmethod
    def create_multiple_response(
        entity_name: str, data: List[Any] = [], message: Optional[str] = None
    ):
        if data:
            return {
                "status": True,
                "responseCode": HTTP_201_CREATED,
                "responseMessage": message or f"{entity_name}s successfully created.",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_400_BAD_REQUEST,
                "responseMessage": f"Failed to create {entity_name}s.",
            }

    @staticmethod
    def verify_response(
        entity_name: str, data: Any = None, message: Optional[str] = None
    ):
        if data:
            return {
                "status": True,
                "responseCode": HTTP_200_OK,
                "responseMessage": message or f"{entity_name} successfully verified.",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_400_BAD_REQUEST,
                "responseMessage": f"Failed to verify {entity_name}.",
            }

    @staticmethod
    def unauthorized_response(message: Optional[str] = None):
        return {
            "status": False,
            "responseCode": HTTP_401_UNAUTHORIZED,
            "responseMessage": message
            or "You are Unauthorized, Please provide a valid access token",
        }

    @staticmethod
    def conflict_response(entity_name: str, message: Optional[str] = None):
        return {
            "status": False,
            "responseCode": HTTP_409_CONFLICT,
            "responseMessage": message or f"user with {entity_name} already exists.",
        }

    @staticmethod
    def get_single_data_response(
        entity_name: str,
        data: Any,
        message: Optional[str] = None,
        code: int = HTTP_200_OK,
    ) -> Any:
        if data:
            return {
                "status": True,
                "responseCode": HTTP_200_OK,
                "responseMessage": message or f"{entity_name} successfully retrieved.",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_404_NOT_FOUND,
                "responseMessage": message or f"{entity_name} not found.",
            }

    @staticmethod
    def get_list_data_response(
        entity_name: str, data: List[Any], message: Optional[str] = None
    ):
        # Always return 200 for list responses, even if empty (better UX for new users)
        return {
            "status": True,
            "responseCode": HTTP_200_OK,
            "responseMessage": message or f"{entity_name}s successfully retrieved.",
            "responseData": data,
        }

    @staticmethod
    def get_paged_data_response(
        entity_name: str,
        data: List[Any],
        total: int,
        page: int,
        page_size: int,
        meta_data: Optional[Any] = None,
        message: Optional[str] = None,
    ):
        # Return 200 with empty array when no data found (not 404)
        return {
            "status": True if data else True,  # Always true for successful query
            "responseCode": HTTP_200_OK,
            "responseMessage": message or f"{entity_name}s successfully retrieved." if data else f"No {entity_name}s found.",
            "responseData": {
                "data": data if data else [],
                "total": total,
                "page": page,
                "pageSize": page_size,
                "metaData": meta_data,
            },
        }

    @staticmethod
    def update_response(
        entity_name: str, data: Any = None, message: Optional[str] = None
    ):
        if data or (data is not None and data.get("status_code", 0) == 200):
            return {
                "status": True,
                "responseCode": HTTP_200_OK,
                "responseMessage": message or f"{entity_name} successfully updated.",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_400_BAD_REQUEST,
                "responseMessage": f"Failed to update {entity_name}.",
            }

    @staticmethod
    def delete_response(
        entity_name: str,
        is_deleted: bool,
        message: Optional[str] = None,
        data: Any = None,
    ):
        if is_deleted:
            return {
                "status": True,
                "responseCode": HTTP_200_OK,
                "responseMessage": message or f"{entity_name} successfully deleted.",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_400_BAD_REQUEST,
                "responseMessage": f"Failed to delete {entity_name}.",
                "responseData": data,
            }

    @staticmethod
    def error_response(message: str, code: int = HTTP_500_INTERNAL_SERVER_ERROR):
        return {
            "status": False,
            "responseCode": code,
            "responseMessage": message,
        }

    @staticmethod
    def login_response(
        entity: str, data: Any, success: bool, message: Optional[str] = None
    ):
        if success:
            return {
                "status": True,
                "responseCode": HTTP_200_OK,
                "responseMessage": message or f"{entity} logged in successfully",
                "responseData": data,
            }
        else:
            return {
                "status": False,
                "responseCode": HTTP_400_BAD_REQUEST,
                "responseMessage": message or f"{entity} login failed",
                "responseData": None,
            }

    @staticmethod
    def custom_response(
        message: Optional[str] = None,
        error_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        success: bool = False,
        data: Any = None,
    ):
        return {
            "status": success,
            "responseCode": error_code,
            "responseMessage": message or "Unable to process your request",
            "responseData": data,
        }
