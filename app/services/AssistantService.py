from app.repository.AssistantRepository import AssistantRepository
from app.domain.requests.assistant_requests import AssistantCreateRequest
from app.domain.responses.uri_response import UriResponse


class AssistantService:
    @staticmethod
    async def create_assistant(request_data: AssistantCreateRequest):
        response = await AssistantRepository.create_assistant(request_data)
        return UriResponse.create_response("assistant", response)

    @staticmethod
    async def list_assistants(limit: int, order: str):
        response = await AssistantRepository.list_assistants(limit, order)
        return UriResponse.get_list_data_response("assistant", response)

    @staticmethod
    async def get_assistant(assistant_id: str):
        response = await AssistantRepository.get_assistant(assistant_id)
        return UriResponse.get_single_data_response("assistant", response)

    @staticmethod
    async def update_assistant(assistant_id: str, request_data: AssistantCreateRequest):
        response = await AssistantRepository.update_assistant(
            assistant_id, request_data
        )
        return UriResponse.update_response("assistant", response)

    @staticmethod
    async def delete_assistant(assistant_id: str):
        response = await AssistantRepository.delete_assistant(assistant_id)
        return UriResponse.delete_response("assistant", response)
