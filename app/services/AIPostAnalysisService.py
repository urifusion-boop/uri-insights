import asyncio
from typing import Any, List, Optional
from app.core.helpers.timer_helper import async_timefunc
from app.domain.enums import ai_prompt
from app.domain.models import chat_model
from app.services.AIService import AIService


class AIPostAnalysisService:
    @async_timefunc
    @staticmethod
    async def generate_ai_post_report(posts) -> Optional[dict]:
        try:
            # Run both sub-parts concurrently
            prompt_base1 = (
                ai_prompt.AIChiefAnalystPrompt.POST_INSIGHTS_SUMMARY_REQUEST_1.value
            )
            prompt_base2 = (
                ai_prompt.AIChiefAnalystPrompt.POST_INSIGHTS_SUMMARY_REQUEST_2.value
            )
            ai_report_content_1 = (
                await AIPostAnalysisService.__generate_ai_post_report_sub_part(
                    posts, prompt_base1, chat_model.InsightSummaryPart1
                )
            )
            ai_report_content_2 = (
                await AIPostAnalysisService.__generate_ai_post_report_sub_part(
                    posts, prompt_base2, chat_model.InsightSummaryPart2
                )
            )

            # Merge and return result
            return {**ai_report_content_1, **ai_report_content_2}

        except Exception as e:
            print("Exception generating AI post report")
            return None

    @staticmethod
    async def __generate_ai_post_report_sub_part(
        posts: List[dict], prompt_base: str, response_model: Any
    ):
        prompt = prompt_base.format(posts=posts)
        model = AIService.build_ai_model(
            messages=[{"role": "user", "content": prompt}], temperature=0.5
        )
        response = (
            await AIService.structured_chat_completion(model, response_model)
        ).dict()
        return response["choices"][0]["message"]["parsed"]
