from app.core.config import settings
from app.services.ApolloService import ApolloService
from app.services.InstagramService import InstagramService
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException


class WebhookService:
    @staticmethod
    def verify_webhook(mode: str, token: str, challenge: str) -> int:
        """
        Verify the webhook subscription request.

        :param mode: Webhook mode (e.g., 'subscribe').
        :param token: Verify token sent by Meta during webhook setup.
        :param challenge: Challenge string to be echoed back.
        :return: Challenge string if verification is successful.
        """
        if mode == "subscribe" and token == settings.WEBHOOK_VERIFY_TOKEN:
            return int(challenge)
        raise HTTPException(status_code=403, detail="Invalid verification token")

    @staticmethod
    async def process_instagram_comment_with_mention_webhook_event(
        db: AsyncIOMotorDatabase, payload: dict
    ):
        """
        Process incoming webhook events from Meta.

        :param payload: JSON payload received from the webhook.
        :return: Processed response or status.
        """
        print("\nWebhook data", payload)

        response = await InstagramService.process_mentions_from_webhook(db, payload)

        return response

    @staticmethod
    async def handle_apollo_webhook(db: AsyncIOMotorDatabase, payload: dict):
        if payload.get("status", "") != "success":
            # Reveal cached phone number
            pass
        people = payload.get("people", [])

        await ApolloService.process_webhook_event(db, people[0])
