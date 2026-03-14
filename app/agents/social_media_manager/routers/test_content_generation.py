from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.agents.social_media_manager.services.content_generation_service import ContentGenerationService

router = APIRouter()

class SimpleContentRequest(BaseModel):
    seed_content: str
    platforms: List[str]
    seed_type: str = "text"

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Social Media Manager Agent is working!", "status": "success"}

@router.post("/generate-content")
async def generate_content(request: SimpleContentRequest):
    """Generate content without authentication for testing"""
    try:
        result = await ContentGenerationService.generate_multi_platform_content(
            user_id="6984ba1ac9172673484fdc5b",  # Your test user ID
            seed_content=request.seed_content,
            platforms=request.platforms,
            seed_type=request.seed_type
        )
        return result
    except Exception as e:
        return {"error": str(e), "details": "Check server logs for more info"}

@router.get("/platform-requirements/{platform}")
async def get_platform_requirements(platform: str):
    """Get platform requirements"""
    try:
        requirements = ContentGenerationService.get_platform_requirements(platform)
        if requirements:
            return {"platform": platform, "requirements": requirements}
        else:
            return {"error": f"Platform {platform} not supported"}
    except Exception as e:
        return {"error": str(e)}