from fastapi import APIRouter
from app.services.AIService import AIService
from app.domain.responses.uri_response import UriResponse

router = APIRouter()


@router.post("/analyze_sentiment")
async def analyze_sentiment(text: str):
    """
    Route to analyze sentiment of a given text
    """
    response = await AIService.analyze_sentiment(text)
    return UriResponse.get_status_response(
        response=response, status_code=response["responseCode"]
    )
