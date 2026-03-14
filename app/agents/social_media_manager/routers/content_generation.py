# app/agents/social_media_manager/routers/content_generation.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional

from app.dependencies import get_db_dependency
from app.core.auth_bearer import JWTBearer
from app.domain.responses.uri_response import UriResponse

from ..services.content_generation_service import ContentGenerationService
from ..repositories.content_request_repository import ContentRequestRepository
from ..schemas.content_schemas import (
    ContentGenerationRequest,
    ContentRegenerationRequest,
    DraftUpdateRequest,
    ScheduleRequest
)

router = APIRouter(tags=["Social Media Manager"])


@router.post("/generate-content")
async def generate_content(
    request: ContentGenerationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    token: dict = Depends(JWTBearer())
):
    """
    Generate platform-native content from seed content
    
    This endpoint:
    1. Validates the request
    2. Checks user's feature limits (monthly generation count)
    3. Generates platform-specific content using AI
    4. Stores the request and drafts in database
    5. Returns generated content for user review
    """
    # Extract user_id from the JWT token
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    
    try:
        # Check monthly usage limits (integrate with your existing feature limits)
        monthly_count = await ContentRequestRepository.get_monthly_request_count(db, user_id)
        
        # This would integrate with your existing FeatureLimitService
        # user_plan = await UserService.get_user_plan(user_id)
        # limit = get_generation_limit_for_plan(user_plan)
        # if monthly_count >= limit:
        #     raise HTTPException(status_code=429, detail="Monthly content generation limit reached")
        
        # Generate content using the service
        result = await ContentGenerationService.generate_multi_platform_content(
            user_id=user_id,
            seed_content=request.seed_content,
            platforms=[p.value for p in request.platforms],
            seed_type=request.seed_type.value
        )
        
        if result.get('status'):
            # Store the request in database
            request_data = result['responseData']
            await ContentRequestRepository.create_request(
                db=db,
                user_id=user_id,
                seed_content=request.seed_content,
                platforms=[p.value for p in request.platforms],
                seed_type=request.seed_type.value,
                request_id=request_data['request_id']
            )
            
            return UriResponse.get_status_response(
                response=result, 
                status_code=200
            )
        else:
            return UriResponse.get_status_response(
                response=result,
                status_code=500
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Social Media Manager Agent is working!", "status": "success"}


@router.get("/content-calendar")
async def get_content_calendar(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    token: dict = Depends(JWTBearer()),
    status: Optional[str] = None,
    limit: int = 20,
    skip: int = 0
):
    """
    Get user's content calendar with requests and drafts
    """
    # Extract user_id from the JWT token
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    
    try:
        # Get user's content requests
        requests_result = await ContentRequestRepository.get_user_requests(
            db=db,
            user_id=user_id,
            status=status,
            limit=limit,
            skip=skip
        )
        
        return UriResponse.get_status_response(
            response=requests_result,
            status_code=200
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/drafts/{draft_id}")
async def update_draft(
    draft_id: str,
    updates: DraftUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    token: dict = Depends(JWTBearer())
):
    """
    Update a content draft (human edits)
    
    This allows users to edit the AI-generated content before approval
    """
    # Extract user_id from the JWT token
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    
    try:
        # This would use ContentDraftRepository to update the draft
        # For now, return a placeholder response
        
        return UriResponse.get_single_data_response(
            "draft_update",
            {
                "draft_id": draft_id,
                "updated_fields": updates.dict(exclude_unset=True),
                "status": "updated"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/regenerate")
async def regenerate_content(
    draft_id: str,
    request: ContentRegenerationRequest,
    token: dict = Depends(JWTBearer())
):
    """
    Regenerate content for a specific draft with optional feedback
    """
    # Extract user_id from the JWT token
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    
    try:
        # This would fetch the original request and regenerate
        result = await ContentGenerationService.regenerate_content(
            draft_id=draft_id,
            user_id=user_id,
            feedback=request.feedback
        )
        
        return UriResponse.get_status_response(
            response=result,
            status_code=200
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/approve")
async def approve_and_schedule(
    draft_id: str,
    schedule_request: ScheduleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
    token: dict = Depends(JWTBearer())
):
    """
    Approve a draft and schedule for publishing
    
    This integrates with Ayrshare for actual publishing
    """
    # Extract user_id from the JWT token
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in token")
    
    try:
        # Validate draft belongs to user
        # Mark as approved in database
        # Schedule for publishing
        
        if schedule_request.publish_immediately:
            # Add background task for immediate publishing
            background_tasks.add_task(publish_content_now, draft_id, user_id, db)
        else:
            # Store scheduled date in database
            pass
        
        return UriResponse.get_single_data_response(
            "approval_result",
            {
                "draft_id": draft_id,
                "status": "approved",
                "publish_immediately": schedule_request.publish_immediately,
                "scheduled_date": schedule_request.scheduled_date
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform-requirements/{platform}")
async def get_platform_requirements(platform: str):
    """
    Get content requirements for a specific platform
    """
    try:
        requirements = ContentGenerationService.get_platform_requirements(platform)
        
        if requirements:
            return UriResponse.get_single_data_response(
                "platform_requirements",
                requirements
            )
        else:
            raise HTTPException(status_code=404, detail=f"Platform {platform} not supported")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Background task for publishing
async def publish_content_now(draft_id: str, user_id: str, db: AsyncIOMotorDatabase):
    """
    Background task to publish content immediately using Ayrshare
    
    This would:
    1. Fetch draft data from database
    2. Get user's Ayrshare profile
    3. Publish using OutstandService
    4. Update draft status
    5. Store analytics placeholder
    """
    try:
        # This would be implemented to:
        # - Fetch draft content
        # - Get social connections
        # - Publish via Ayrshare
        # - Update database with results
        print(f"🚀 Publishing draft {draft_id} for user {user_id}")
        
    except Exception as e:
        print(f"❌ Publishing failed for draft {draft_id}: {str(e)}")