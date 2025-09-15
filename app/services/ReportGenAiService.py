from typing import Any, Dict, List, Optional, Type, Union
from app.domain.enums import ai_prompt
from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum
from app.domain.models import chat_model
from app.domain.responses.reportgeneration_response import (
    AIIndustryClassification,
    ActivityOverviewAiResponse,
    KPIAnalysis,
    SummaryAndAchievement,
)
from app.services.AIService import AIService


class ReportGenAiService:
    report_type_to_prompt_map: Dict[
        ReportGenerationTypeEnum,
        Type[
            Union[
                ai_prompt.AccountTrackingReportGenPrompt,
                ai_prompt.HashtagTrackingReportGenPrompt,
            ]
        ],
    ] = {
        ReportGenerationTypeEnum.ACCOUNT_TRACKING: ai_prompt.AccountTrackingReportGenPrompt,
        ReportGenerationTypeEnum.HASHTAG_TRACKING: ai_prompt.HashtagTrackingReportGenPrompt,
    }

    @staticmethod
    async def get_account_name(
        metadata: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ) -> Optional[str]:
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )

        account_metadata = {
            key: value.get("account_info") for key, value in metadata.items()
        }

        prompt = prompt_cls.ACCOUNT_NAME.value.format(account_metadata=account_metadata)

        try:
            account_name = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=chat_model.PlainText
            )
            return account_name.get("text", "Nil")
        except Exception as e:
            print("Exception in getting account name: ", e)
            raise

    @staticmethod
    async def generate_ai_report_overview(
        account_overview: dict,
        report_focus: str,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ) -> Optional[dict]:
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.REPORT_OVERVIEW.value.format(
            account_overview=account_overview, report_focus=report_focus
        )
        try:
            ai_report_overview = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=chat_model.ReportGenerationOverview
            )
            return ai_report_overview
        except Exception as e:
            print("Exception in generating AI report overview: ", e)
            raise

    @staticmethod
    async def generate_report_highlights(
        current_period_insights: dict,
        previous_period_insights: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ) -> Optional[dict]:
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.REPORT_GEN_HIGHLIGHTS.value.format(
            current_period_insights=current_period_insights,
            previous_period_insights=previous_period_insights,
        )
        try:
            ai_report_highlights = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=chat_model.ReportGenerationHighlights
            )
            return ai_report_highlights
        except Exception as e:
            print("Exception in generating AI report highlights: ", e)
            raise

    @staticmethod
    async def generate_report_performance_section_text(
        account_info: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ) -> Optional[dict]:
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.PERFORMANCE_SECTION_TEXT.value.format(
            account_info=account_info
        )
        try:
            ai_performance_section_text = (
                await ReportGenAiService.__generate_ai_content(
                    prompt=prompt,
                    response_model=chat_model.ReportGenerationGenericTextResult,
                )
            )
            return ai_performance_section_text.get("text")
        except Exception as e:
            print("Exception in generating AI report highlights: ", e)
            raise

    @staticmethod
    async def generate_kpi_analysis(
        kpi_performance_summary: dict,
        post_data: List[dict],
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ) -> Optional[dict]:
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        post_data = post_data[:20]
        prompt = prompt_cls.KPI_ANALYSIS.value.format(
            kpi_performance_summary=kpi_performance_summary,
            post_data=post_data,
        )
        try:
            ai_kpi_analysis = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=KPIAnalysis
            )
            return ai_kpi_analysis
        except Exception as e:
            print("Exception in generating AI report highlights: ", e)
            raise

    @staticmethod
    async def generate_summary_and_achievements(
        data: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ):
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.SUMMARY_AND_ACHIEVEMENTS.value.format(
            data=data,
        )
        try:
            ai_summary_and_achievements = (
                await ReportGenAiService.__generate_ai_content(
                    prompt=prompt, response_model=SummaryAndAchievement
                )
            )
            return ai_summary_and_achievements
        except Exception as e:
            print("Exception in generating AI summary and achievements data: ", e)
            raise

    @staticmethod
    async def generate_activity_overview(
        post_data: List[dict],
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ):
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.ACTIVITY_OVERVIEW.value.format(
            post_data=post_data,
        )
        try:
            activity_overview = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=ActivityOverviewAiResponse
            )
            return activity_overview
        except Exception as e:
            print("Exception in generating AI activity overview data: ", e)
            raise

    @staticmethod
    async def generate_ai_industry_classification(
        data: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ):
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.AI_INDUSTRY_CLASSIFICATION.value.format(
            data=data,
        )
        try:
            ai_industry_classification = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=AIIndustryClassification
            )
            return ai_industry_classification
        except Exception as e:
            print("Exception in generating AI industry classification data: ", e)
            raise

    @staticmethod
    async def generate_top_suggested_improvement(
        data: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ):
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.TOP_SUGGESTED_IMPROVEMENT.value.format(
            data=data,
        )
        try:
            improvement_data = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=chat_model.TopSuggestedImprovementsList
            )
            return improvement_data.get("data")
        except Exception as e:
            print("Exception in generating top suggested improvement: ", e)
            raise

    @staticmethod
    async def generate_ai_recommendations(
        data: dict,
        report_type: ReportGenerationTypeEnum = ReportGenerationTypeEnum.ACCOUNT_TRACKING,
    ):
        prompt_cls = ReportGenAiService.report_type_to_prompt_map.get(
            report_type, ai_prompt.AccountTrackingReportGenPrompt
        )
        prompt = prompt_cls.AI_RECOMMENDATIONS.value.format(
            data=data,
        )
        try:
            recommendation_data = await ReportGenAiService.__generate_ai_content(
                prompt=prompt, response_model=chat_model.AIRecommendation
            )
            return recommendation_data.get("recommendations", [])
        except Exception as e:
            print("Exception in generating AI recommendations: ", e)
            raise

    @staticmethod
    async def __generate_ai_content(prompt: str, response_model: Any):
        model = AIService.build_ai_model(
            messages=[{"role": "user", "content": prompt}], temperature=0.5
        )

        ai_response = (
            await AIService.structured_chat_completion(model, response_model)
        ).dict()

        try:
            ai_response_content = ai_response["choices"][0]["message"]["parsed"]
            return ai_response_content
        except Exception as e:
            print("Exception in generating ai report content: ", e)
            raise
