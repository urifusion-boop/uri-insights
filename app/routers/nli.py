from fastapi import APIRouter
from app.domain.responses.uri_response import UriResponse
from app.services.nli_agents.NliAgentOrchestrator import NliAgentOrchestrator

router = APIRouter()


@router.post("/user-prompt/process")
async def process_user_prompt(user_id: str, prompt: str):
    response = await NliAgentOrchestrator.process_user_prompt(prompt, user_id)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
