from collections import defaultdict
from datetime import datetime
from typing import Any, Collection, List, Dict

from app.domain.models.chat_model import ChatModel
from app.domain.requests.mention_requests import AlertAnalyticsRequest
from app.domain.responses.mention_response import (
    AiRecommendationResponse,
    AlertAnalyticsResponse,
)
from app.domain.responses.uri_response import UriResponse
from app.repository.MentionRepository import MentionRepository
from app.services.AIService import AIService


class MentionService:
    @staticmethod
    async def generate_alert_analytics(db: Collection, request: AlertAnalyticsRequest):
        alerts = (await MentionRepository.fetch_alerts_by_date_range(db, request)).get(
            "responseData"
        )
        alert_sentiment_analysis = await MentionService.get_alerts_sentiment_analysis(
            alerts=alerts
        )
        ai_recommendation = await MentionService.generate_ai_analytics_recommendation(
            alerts
        )
        analytics_over_time = (
            await MentionService.get_alert_sentiment_analytics_over_time(alerts)
        )
        alert_analytics = AlertAnalyticsResponse(
            high_priority_alerts=await MentionService.get_high_priority_alerts(alerts),
            **alert_sentiment_analysis,
            ai_recommendation=ai_recommendation,
            analytics_over_time=analytics_over_time,
        )

        return UriResponse.get_single_data_response("Alert analytics", alert_analytics)

    @staticmethod
    async def generate_ai_analytics_recommendation(comments: List[str]):
        prompt = f"""
        You are an advanced operations manager and business analyst with expertise in reputation management and customer experience.
        Base on the online comments about a business along with the sentiment analysis insights below.
        Identify key trends, recurring concerns, and opportunities for improvement.
        Then, craft a concise and strategic recommendation that includes specific action points to enhance customer satisfaction, brand perception, and business performance.
        Your response should be less than 100 words practical, data-driven, aligned with industry best practices and contain a title that communicates the next action step or summarizes the recommendation.

        {comments[:50]}
        """

        model = AIService.build_ai_model(
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}",
                }
            ]
        )

        try:
            # Parse AI response
            ai_response = (
                await AIService.structured_chat_completion(
                    model, AiRecommendationResponse
                )
            ).dict()

            response = ai_response["choices"][0]["message"]["parsed"]

            # Return the parsed lead directly
            return response
        except Exception as e:
            print(f"Error while generating AI recommendation: {e}")
            return None

    @staticmethod
    async def get_alerts_sentiment_analysis(alerts: List[dict]):
        total_alerts = len(alerts)
        positive_alerts = 0
        negative_alerts = 0
        for alert in alerts:
            alert["_id"] = str(alert["_id"])
            if alert.get("sentiment") == "positive":
                positive_alerts += 1
            elif alert.get("sentiment") == "negative":
                negative_alerts += 1
        neutral_alerts = total_alerts - (positive_alerts + negative_alerts)

        # Platform breakdown
        platform_breakdown: Dict[Any, Any] = {}
        for alert in alerts:
            platform = alert.get("platform", "OTHERS")
            sentiment = alert.get("sentiment")
            if sentiment:
                if platform not in platform_breakdown:
                    platform_breakdown = {**platform_breakdown, platform: {}}
                if sentiment in platform_breakdown.get(platform, {}):
                    platform_breakdown[platform][sentiment] += 1
                else:
                    platform_breakdown[platform][sentiment] = 1

        response = {
            "total_alerts": total_alerts,
            "positive_alerts": positive_alerts,
            "negative_alerts": negative_alerts,
            "neutral_alerts": neutral_alerts,
            "platform_breakdown": platform_breakdown,
        }
        return response

    @staticmethod
    async def get_alert_sentiment_analytics_over_time(alerts: List[dict]):
        analytics_over_time: defaultdict = defaultdict(dict)

        for alert in alerts:
            sentiment = alert.get("sentiment", "")
            day: int = alert["created_at"].day
            month: str = alert["created_at"].strftime("%b")
            day_sentiment_analysis_dict = analytics_over_time[month + " " + str(day)]
            if sentiment in day_sentiment_analysis_dict:
                day_sentiment_analysis_dict[sentiment] += 1
            else:
                day_sentiment_analysis_dict[sentiment] = 1
        return dict(analytics_over_time)

    @staticmethod
    async def get_high_priority_alerts(alerts: List[dict]):
        priority_order = {"High": 3, "Medium": 2, "Low": 1}

        sorted_alerts = sorted(
            alerts, key=lambda x: priority_order[x["sentiment_priority"]], reverse=True
        )

        return sorted_alerts[:3]
