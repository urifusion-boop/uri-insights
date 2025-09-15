from typing import Dict, List, Union
from app.core.config import settings
from app.domain.enums.aithread_enum import AiThreadTypeEnum
from app.repository.TrackerRepository import TrackerRepository
from app.repository.InfluencerRepository import InfluencerRepository
from motor.motor_asyncio import AsyncIOMotorDatabase


class AssistantHelper:
    """
    Helper class to map thread types to the correct Assistant ID and initial message.
    """

    ASSISTANT_MAPPING: Dict[str, str] = {
        AiThreadTypeEnum.KEYWORD_TRACKING_INSIGHTS.value: settings.KEYWORD_TRACKING_ASSISTANT_ID,
        AiThreadTypeEnum.CONTENT_MANAGEMENT_INSIGHTS.value: settings.CONTENT_MANAGEMENT_ASSISTANT_ID,
        AiThreadTypeEnum.HASHTAG_TRACKING_INSIGHTS.value: settings.HASHTAG_TRACKING_ASSISTANT_ID,
        AiThreadTypeEnum.ACCOUNT_TRACKING_INSIGHTS.value: settings.ACCOUNT_TRACKING_ASSISTANT_ID,
        AiThreadTypeEnum.LEAD_TRACKING_INSIGHTS.value: settings.LEAD_TRACKING_ASSISTANT_ID,
    }

    DEFAULT_MESSAGES: Dict[str, str] = {
        AiThreadTypeEnum.KEYWORD_TRACKING_INSIGHTS.value: "👋 Want to chat about a keyword? I’m an AI assistant here to answer your questions.",
        AiThreadTypeEnum.CONTENT_MANAGEMENT_INSIGHTS.value: "Hello! Need insights on your content strategy? I'm here to help.",
        AiThreadTypeEnum.HASHTAG_TRACKING_INSIGHTS.value: "📌 Let's analyze hashtag trends! Which hashtag would you like to explore?",
        AiThreadTypeEnum.ACCOUNT_TRACKING_INSIGHTS.value: "🔍 Want to monitor an account? I can provide insights on its activity.",
        AiThreadTypeEnum.LEAD_TRACKING_INSIGHTS.value: "Hello! 🌟 I'm your lead-finding assistant. Describe who you're looking for and I'll track them down! 🚀",
    }

    @staticmethod
    def get_assistant_id_for_thread_type(thread_type: str) -> str:
        """
        Returns the assistant_id based on the thread type.
        """
        assistant_id = AssistantHelper.ASSISTANT_MAPPING.get(thread_type)

        if not assistant_id:
            raise ValueError(f"Invalid thread type: {thread_type}")

        return assistant_id

    @staticmethod
    async def get_initial_message_for_thread_type(
        db: AsyncIOMotorDatabase, thread_type: str, user_id: str
    ) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]:
        """
        Returns the default assistant message or a list of buttons for hashtag/account tracking.
        """

        # Handle Hashtag Tracking Insights
        if thread_type == AiThreadTypeEnum.HASHTAG_TRACKING_INSIGHTS.value:
            tracker_names = await TrackerRepository.get_tracker_names_by_user(
                db, user_id
            )

            if not tracker_names:
                return [
                    {
                        "type": "text",
                        "text": "📌 No hashtag trackers found. Start tracking hashtags now!",
                    }
                ]

            hashtag_buttons: List[Dict[str, str]] = [
                {"type": "button", "text": f"#{tracker}", "value": tracker}
                for tracker in tracker_names
            ]

            return [
                {
                    "type": "text",
                    "text": "📌 Let's analyze hashtag trends! Select a hashtag below:",
                },
                {"type": "buttons", "buttons": hashtag_buttons},  # ✅ Fixed type issue
            ]

        # Handle Account Tracking Insights
        elif thread_type == AiThreadTypeEnum.ACCOUNT_TRACKING_INSIGHTS.value:
            social_usernames = await InfluencerRepository.get_social_usernames_by_user(
                db, user_id
            )

            if not social_usernames:
                return [
                    {
                        "type": "text",
                        "text": "🔍 No accounts being tracked. Start tracking accounts now!",
                    }
                ]

            account_buttons: List[Dict[str, str]] = [
                {
                    "type": "button",
                    "text": f"{username} ({platform})",
                    "value": username,
                }
                for username, platform in social_usernames  # ✅ Proper tuple unpacking
            ]

            return [
                {"type": "text", "text": "🔍 Select an account to analyze insights:"},
                {"type": "buttons", "buttons": account_buttons},  # ✅ Fixed MyPy issue
            ]

        # Default response for other thread types
        return [
            {
                "type": "text",
                "text": AssistantHelper.DEFAULT_MESSAGES.get(thread_type, "Hello!"),
            }
        ]
