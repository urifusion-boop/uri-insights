# app/agents/social_media_manager/routers/test_complete_social_manager.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse

# Import your working services
from ..services.content_generation_service import ContentGenerationService

router = APIRouter(tags=["Social Media Manager"])

# Simplified models for testing
class ContentGenerationRequest(BaseModel):
    seed_content: str = Field(..., min_length=10, max_length=5000)
    platforms: List[str] = Field(..., min_items=1, max_items=5)
    seed_type: str = "text"
    include_images: bool = False
    brand_context: Optional[Dict[str, Any]] = None

class SocialConnectionRequest(BaseModel):
    platforms: List[str] = Field(..., min_items=1, max_items=5)

# Test endpoints without authentication
@router.post("/generate-content")
async def generate_content(request: ContentGenerationRequest):
    """Generate content without auth for testing"""
    try:
        # Use your working content generation service
        result = await ContentGenerationService.generate_multi_platform_content(
            user_id="6984ba1ac9172673484fdc5b",  # Your test user
            seed_content=request.seed_content,
            platforms=request.platforms,
            seed_type=request.seed_type
        )
        
        # If images requested, add mock image data
        if request.include_images and result.get('status'):
            for draft in result['responseData']['drafts']:
                draft['has_image'] = True
                draft['image_url'] = f"https://mock-dalle-image.com/{draft['platform']}-{hash(draft['content'])}.png"
                draft['image_specs'] = {"width": 1200, "height": 628, "format": "landscape"}
            
            result['responseData']['images_generated'] = len(result['responseData']['drafts'])
            result['responseData']['image_errors'] = []
        
        return result
        
    except Exception as e:
        return {"error": str(e), "details": "Check server logs"}

@router.post("/connect/initiate")
async def initiate_social_connections(request: SocialConnectionRequest):
    """Social account connection initiation using Outstand (no auth, test only)"""
    try:
        from ..services.social_account_service import SocialAccountService

        result = await SocialAccountService.initiate_connection_flow(
            user_id="6984ba1ac9172673484fdc5b",
            platforms=request.platforms,
        )
        return result

    except Exception as e:
        return {"error": str(e), "details": "Check your OUTSTAND_API_KEY"}

@router.get("/connections")
async def get_user_connections():
    """Get mock user connections"""
    return UriResponse.get_single_data_response("user_connections", {
        "user_id": "6984ba1ac9172673484fdc5b",
        "connected_platforms": ["linkedin", "twitter"],
        "connections": {
            "linkedin": {
                "id": "conn_linkedin_123",
                "username": "@uricreative",
                "display_name": "URI Creative",
                "status": "active",
                "posts_published": 5,
                "connected_at": "2026-02-26T08:00:00"
            },
            "twitter": {
                "id": "conn_twitter_456", 
                "username": "@uri_insights",
                "display_name": "URI Insights",
                "status": "active",
                "posts_published": 12,
                "connected_at": "2026-02-26T08:15:00"
            }
        },
        "total_connections": 2,
        "note": "Mock data - connect real accounts via Ayrshare"
    })

@router.post("/approve")
async def approve_content(
    draft_ids: List[str],
    schedule_option: str = "save_draft",
    scheduled_datetime: Optional[str] = None
):
    """Test content approval"""
    return UriResponse.get_single_data_response("content_approval", {
        "approved_drafts": [{"draft_id": draft_id, "status": "approved"} for draft_id in draft_ids],
        "schedule_option": schedule_option,
        "scheduled_datetime": scheduled_datetime,
        "approved_at": datetime.utcnow().isoformat(),
        "note": "Mock approval - would update database and trigger publishing"
    })

@router.post("/deny")
async def deny_content(
    draft_ids: List[str],
    denial_reason: str,
    request_regeneration: bool = False
):
    """Test content denial"""
    return UriResponse.get_single_data_response("content_denial", {
        "denied_drafts": draft_ids,
        "denial_reason": denial_reason,
        "regeneration_requested": request_regeneration,
        "denied_at": datetime.utcnow().isoformat()
    })

@router.get("/content-calendar")
async def get_content_calendar():
    """Mock content calendar"""
    return UriResponse.get_single_data_response("content_calendar", {
        "user_id": "6984ba1ac9172673484fdc5b",
        "drafts": [
            {
                "id": "draft_123",
                "platform": "linkedin", 
                "content": "Sample LinkedIn content...",
                "status": "draft",
                "created_at": "2026-02-26T09:30:00"
            },
            {
                "id": "draft_456",
                "platform": "twitter",
                "content": "Sample Twitter thread...",
                "status": "approved", 
                "created_at": "2026-02-26T10:00:00"
            }
        ],
        "total_count": 2
    })

@router.get("/test")
async def test_endpoint():
    """Health check"""
    return {
        "message": "Complete Social Media Manager is working!",
        "status": "success",
        "workflow": [
            "1. Connect social accounts",
            "2. Generate AI content + images", 
            "3. Approve/deny/refine content",
            "4. Schedule and publish"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }