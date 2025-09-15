from fastapi import APIRouter
from app.services.AssistantService import AssistantService
from app.domain.requests.assistant_requests import AssistantCreateRequest
from app.domain.responses.uri_response import UriResponse

router = APIRouter()


@router.post("/create", summary="Create a new AI Assistant")
async def create_assistant(request_data: AssistantCreateRequest):
    response = await AssistantService.create_assistant(request_data)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.get("/getAll", summary="List AI Assistants")
async def list_assistants(limit: int = 20, order: str = "desc"):
    response = await AssistantService.list_assistants(limit, order)
    return UriResponse.get_status_response(response=response)


@router.get("/getById/{assistant_id}", summary="Retrieve an AI Assistant by ID")
async def get_assistant(assistant_id: str):
    response = await AssistantService.get_assistant(assistant_id)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.post("/update", summary="Update an existing AI Assistant")
async def update_assistant(assistant_id: str, request_data: AssistantCreateRequest):
    response = await AssistantService.update_assistant(assistant_id, request_data)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )


@router.delete("/delete/{assistant_id}", summary="Delete an AI Assistant")
async def delete_assistant(assistant_id: str):
    response = await AssistantService.delete_assistant(assistant_id)
    return UriResponse.get_status_response(
        response=response, status_code=response.get("responseCode", "")
    )
