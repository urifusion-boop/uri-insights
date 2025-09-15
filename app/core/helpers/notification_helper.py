from app.core.config import settings
from app.core.helpers.lead_helper import LeadHelper
from app.core.helpers.user_helper import UserHelper
from app.domain.enums.notification_enum import NotificationSubjectEnum


class NotificationHelper:
    @staticmethod
    async def set_lead_alert_data(lead: dict) -> dict | None:
        print("Preparing notification for lead:", lead)

        if not lead or not lead.get("assigned_to"):
            print("Invalid lead data for notification")
            return None

        keywords = lead.get("keywords", [])

        notification_data = {
            "userId": lead.get("assigned_to"),
            "leadName": NotificationSubjectEnum.NEW_LEAD.value,
            "keyword": (
                ", ".join(keywords) if keywords else ""
            ),  # Get first keyword if available
            "platform": "Social Media",
            "time": "Now",
            "author": lead.get("username", ""),
            "comment": lead.get("mention", ""),
            "sentimentPriority": lead.get("interest_level", "Low"),
            "commentSummary": lead.get("summary_of_mention", ""),
            "viewLeadLink": f"https://{settings.WEB_APP_URL}/leads/{lead.get('username', '')}",
        }

        return notification_data  # Returning a dictionary, not an object

    @staticmethod
    async def set_mention_alert_data(mention: dict) -> dict | None:
        print("Preparing notification for alert:", mention)

        if not mention:
            print("Mention data for notification")
            return None

        notification_data = {
            "userId": mention.get("user_id"),
            "author": mention.get("author", ""),
            "keyword": mention.get("keyword", ""),
            "alertName": NotificationSubjectEnum.HIGH_PRIORITY_MENTION.value,
            "platform": mention.get("platform", ""),
            "time": "Now",
            "comment": mention.get("comment", ""),
            "sentimentPriority": mention.get("sentiment_priority", "Low"),
            "viewLeadLink": f"https://{settings.WEB_APP_URL}/alert",
        }

        return notification_data

    @staticmethod
    async def build_base_lead_notification_payload(
        user_id: str, form_type: str
    ) -> dict:
        email = await UserHelper.get_user_email(user_id)
        return {
            "userId": user_id,
            "email": email,
            "leadType": LeadHelper.get_lead_type_for_notification(form_type),
        }

    @staticmethod
    async def build_extended_lead_notification_payload(
        user_id: str, form_type: str, extra: dict
    ) -> dict:
        base = await NotificationHelper.build_base_lead_notification_payload(
            user_id, form_type
        )
        base.update(extra)
        return base
