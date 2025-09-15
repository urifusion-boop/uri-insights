import json
from app.dependencies import get_db_dependency
from fastapi import APIRouter, Request, HTTPException, Depends
from app.services.WebhookService import WebhookService
from motor.motor_asyncio import AsyncIOMotorDatabase


router = APIRouter()


@router.get("/meta-webhook", tags=["Meta Webhook"])
async def verify_meta_webhook(request: Request):
    """
    Verifies the webhook subscription request from Meta.

    **Query Parameters**:
    - `hub_mode`: Mode of the webhook request (e.g., 'subscribe').
    - `hub_verify_token`: Token to verify the webhook.
    - `hub_challenge`: Challenge string to respond back.
    """
    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    return WebhookService.verify_webhook(hub_mode, hub_verify_token, hub_challenge)


@router.post("/meta-webhook", tags=["Meta Webhook"])
async def handle_meta_webhook_event(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Processes incoming webhook events from Meta.

    **Body**: JSON payload containing the event data.
    """
    payload = await request.json()
    print("Webhook Payload:", payload)

    if "object" not in payload or payload["object"] != "instagram":
        raise HTTPException(status_code=400, detail="Invalid webhook event")

    return await WebhookService.process_instagram_comment_with_mention_webhook_event(
        db, payload
    )


@router.post("/apollo-webhook", tags=["Apollo Webhook"])
async def handle_apollo_webhook_event(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    payload = await request.json()
    print("APOLLO Webhook payload: ", payload)

    return await WebhookService.handle_apollo_webhook(db=db, payload=payload)
