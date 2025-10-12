from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.BrowsercloudService import BrowsercloudService
from app.services.AIService import AIService
from app.services.LeadNotificationManager import LeadNotificationManager
from app.domain.schemas.browsercloud_schema import BrowsercloudSocialPost
from app.domain.schemas.realtime_lead_schema import (
    RealtimeLead,
    RealtimeLeadSource,
    RealtimeLeadBatch,
)
from app.repository.RealtimeLeadRepository import RealtimeLeadRepository
from app.repository.LeadFormRepository import LeadFormRepository
from app.core.config import settings


class RealtimeLeadProcessor:
    def __init__(self):
        self.browsercloud_service = BrowsercloudService()
        self.notification_manager = LeadNotificationManager()

    async def process_browsercloud_webhook(
        self,
        db: AsyncIOMotorDatabase,
        payload: dict,
        signature: str
    ) -> dict:
        """Process incoming webhook from Browsercloud."""
        try:
            # Validate and process posts from webhook
            posts = await self.browsercloud_service.handle_webhook_payload(
                payload, signature
            )
            
            if not posts:
                return {
                    "status": True,
                    "message": "No new posts to process",
                    "leads_created": 0
                }

            # Process posts into leads
            leads = await self._create_leads_from_posts(db, posts)
            
            # Save leads batch
            batch = RealtimeLeadBatch(
                leads=leads,
                task_id=payload.get("task_id"),
                platform=payload.get("platform")
            )
            
            result = await RealtimeLeadRepository.save_lead_batch(db, batch)
            
            # Send real-time notifications for new leads
            for lead in leads:
                await self.notification_manager.handle_new_lead(lead.dict())
            
            return {
                "status": True,
                "message": "Successfully processed webhook",
                "leads_created": len(leads)
            }

        except Exception as e:
            return {
                "status": False,
                "message": f"Error processing webhook: {str(e)}",
                "leads_created": 0
            }

    async def _create_leads_from_posts(
        self,
        db: AsyncIOMotorDatabase,
        posts: List[BrowsercloudSocialPost]
    ) -> List[RealtimeLead]:
        """Convert social media posts to leads."""
        leads = []
        
        for post in posts:
            # Find matching lead forms based on keywords and signals
            matching_forms = await self._find_matching_lead_forms(
                db, post.matched_keywords, post.matched_signals
            )
            
            for form in matching_forms:
                # Create lead source
                source = RealtimeLeadSource(
                    platform=post.platform,
                    post_url=post.url,
                    post_content=post.content,
                    author_name=post.author_name,
                    author_handle=post.author_handle,
                    author_url=post.author_url,
                    posted_at=post.posted_at,
                    engagement_metrics=post.engagement_metrics,
                    matched_keywords=post.matched_keywords,
                    matched_signals=post.matched_signals,
                    raw_data=post.dict()
                )
                
                # Generate AI reply suggestion
                ai_reply = await self._generate_ai_reply(
                    form.get("ai_response_guide", ""),
                    post.content,
                    form.get("business_summary", "")
                )
                
                # Create lead
                lead = RealtimeLead(
                    user_id=form["user_id"],
                    lead_form_id=form["lead_form_id"],
                    source=source,
                    ai_suggested_reply=ai_reply
                )
                
                leads.append(lead)
        
        return leads

    async def _find_matching_lead_forms(
        self,
        db: AsyncIOMotorDatabase,
        keywords: List[str],
        signals: List[str]
    ) -> List[dict]:
        """Find lead forms that match the keywords and signals."""
        # Query for lead forms that have matching keywords or signals
        query = {
            "$or": [
                {"keywords": {"$in": keywords}},
                {"buying_signals": {"$in": signals}}
            ],
            "disabled": False
        }
        
        cursor = db[LeadFormRepository.collection_name].find(query)
        return await cursor.to_list(length=None)

    async def _generate_ai_reply(
        self,
        response_guide: str,
        post_content: str,
        business_summary: str
    ) -> str:
        """Generate AI-suggested reply for the lead."""
        prompt = f"""
        Based on the following context, generate a natural, engaging response:
        
        Business Context: {business_summary}
        
        Response Guidelines: {response_guide}
        
        Original Post: {post_content}
        
        Generate a response that:
        1. Is friendly and professional
        2. Addresses the specific need/interest shown in the post
        3. Introduces the business naturally
        4. Includes a clear value proposition
        5. Encourages further engagement
        """
        
        try:
            messages = [{"role": "user", "content": prompt}]
            model = AIService.build_ai_model(messages=messages)
            response = await AIService.chat_completion(model)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating AI reply: {e}")
            return ""