from fastapi import APIRouter, Header, Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.RealtimeLeadProcessor import RealtimeLeadProcessor
from app.database import get_db

router = APIRouter()
lead_processor = RealtimeLeadProcessor()

@router.post("/browsercloud")
async def handle_browsercloud_webhook(
    request: Request,
    x_browsercloud_signature: str = Header(...),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Handle incoming webhooks from Browsercloud."""
    try:
        payload = await request.json()
        
        result = await lead_processor.process_browsercloud_webhook(
            db,
            payload,
            x_browsercloud_signature
        )
        
        if not result["status"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
        )