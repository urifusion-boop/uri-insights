"""
Signal Refinery Service - "Trash Compactor" + "LLM Sanitizer"

Implements the filtering pipeline from the suggestion:
1. Rules-Based Pre-Filtering (Trash Compactor)
2. LLM Buyer/Seller Classification (LLM Sanitizer)

This is the "Intelligence Layer" that turns raw Google results into qualified leads.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from app.services.AIService import AIService
from app.domain.schemas.signal_refinery_schema import (
    XRaySearchResult,
    FilteredResult,
    FilterReasonEnum,
    BuyerSellerEnum,
    BuyerSellerClassification,
    XRayLead,
    RefineryMetrics
)

logger = logging.getLogger(__name__)


class BuyerSellerAnalysisResult(BaseModel):
    """Structured response from LLM buyer/seller classification"""
    classification: str = Field(description="'buyer', 'seller', or 'unknown'")
    confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")
    reasoning: str = Field(description="Why this is a buyer or seller")
    pain_point: Optional[str] = Field(default=None, description="If buyer, what's their pain?")
    product_needed: Optional[str] = Field(default=None, description="If buyer, what do they need?")


class SignalRefineryService:
    """
    The "Signal Refinery" - Filters and classifies search results

    Pipeline:
    1. Blocklist filter (crypto, forex, spam)
    2. Bot pattern detection
    3. Nigerian entity check
    4. Duplicate detection
    5. LLM buyer/seller classification
    """

    # ========================================
    # STEP 1: BLOCKLIST (The "Global Noise" Filter)
    # ========================================

    # Keywords that indicate spam/irrelevant content
    BLOCKLIST = [
        "crypto", "cryptocurrency", "bitcoin", "ethereum",
        "forex", "trading signals", "binary options",
        "nft", "nfts", "blockchain",
        "dating", "hookup", "singles",
        "betting", "casino", "gambling",
        "giveaway", "airdrop", "free money",
        "mlm", "pyramid", "get rich quick",
        "work from home", "make money online",
        "adult content", "xxx"
    ]

    # ========================================
    # STEP 2: BOT PATTERNS (The "Bot Detector")
    # ========================================

    BOT_PATTERNS = [
        "limited time offer",
        "click link in bio",
        "click here",
        "dm for rates",
        "dm for price",
        "send dm",
        "link in bio",
        "whatsapp only",
        "inbox me",
        "pm me",
        "text me on",
        "hurry now",
        "last chance",
        "act fast",
        "don't miss out"
    ]

    # ========================================
    # STEP 3: NIGERIAN ENTITY MARKERS
    # ========================================

    NIGERIAN_MARKERS = [
        # Cities
        "lagos", "abuja", "port harcourt", "ibadan", "kano",
        "jos", "benin city", "kaduna", "enugu", "owerri",
        "calabar", "warri", "abeokuta", "ilorin", "ogbomosho",

        # Currency
        "₦", "naira", "ngn",

        # Country
        "nigeria", "nigerian",

        # Local terms
        "lekki", "vi", "ikeja", "surulere", "festac",
        "garki", "wuse", "gwarinpa",  # Abuja areas
        "nepa", "phcn",  # Electricity
        "danfo", "okada",  # Transportation
    ]

    def __init__(self):
        """Initialize AI service for LLM classification"""
        self.ai_service = AIService()

    # ========================================
    # FILTERING METHODS
    # ========================================

    def apply_blocklist_filter(
        self,
        results: List[XRaySearchResult]
    ) -> Tuple[List[XRaySearchResult], List[FilteredResult]]:
        """
        STEP 1: Filter out spam keywords

        Returns:
            (passed_results, filtered_results)
        """
        passed = []
        filtered = []

        for result in results:
            # Combine title and snippet for checking
            text = f"{result.title} {result.snippet}".lower()

            # Check against blocklist
            matched_terms = [term for term in self.BLOCKLIST if term in text]

            if matched_terms:
                # FILTERED: Contains spam keywords
                filtered.append(FilteredResult(
                    result=result,
                    filter_reason=FilterReasonEnum.BLOCKLIST,
                    filter_detail=f"Matched blocklist: {', '.join(matched_terms)}"
                ))
            else:
                passed.append(result)

        logger.info(f"   📋 Blocklist filter: {len(passed)}/{len(results)} passed, {len(filtered)} filtered")
        return passed, filtered

    def apply_bot_pattern_filter(
        self,
        results: List[XRaySearchResult]
    ) -> Tuple[List[XRaySearchResult], List[FilteredResult]]:
        """
        STEP 2: Filter out bot/spam patterns

        Returns:
            (passed_results, filtered_results)
        """
        passed = []
        filtered = []

        for result in results:
            text = f"{result.title} {result.snippet}".lower()

            # Check against bot patterns
            matched_patterns = [pattern for pattern in self.BOT_PATTERNS if pattern in text]

            if matched_patterns:
                # FILTERED: Looks like a bot/spam
                filtered.append(FilteredResult(
                    result=result,
                    filter_reason=FilterReasonEnum.BOT_PATTERN,
                    filter_detail=f"Matched bot pattern: {', '.join(matched_patterns)}"
                ))
            else:
                passed.append(result)

        logger.info(f"   🤖 Bot filter: {len(passed)}/{len(results)} passed, {len(filtered)} filtered")
        return passed, filtered

    def apply_nigerian_entity_filter(
        self,
        results: List[XRaySearchResult],
        enabled: bool = True
    ) -> Tuple[List[XRaySearchResult], List[FilteredResult]]:
        """
        STEP 3: Check for Nigerian entity markers

        If enabled=False, all results pass (for non-Nigerian use cases)

        Returns:
            (passed_results, filtered_results)
        """
        if not enabled:
            logger.info(f"   🇳🇬 Nigerian filter: DISABLED (all {len(results)} passed)")
            return results, []

        passed = []
        filtered = []

        for result in results:
            text = f"{result.title} {result.snippet}".lower()

            # Check for Nigerian markers
            has_nigerian_marker = any(marker in text for marker in self.NIGERIAN_MARKERS)

            if has_nigerian_marker:
                passed.append(result)
            else:
                # FILTERED: No Nigerian entity found
                filtered.append(FilteredResult(
                    result=result,
                    filter_reason=FilterReasonEnum.NOT_NIGERIAN,
                    filter_detail="No Nigerian location/currency markers found"
                ))

        logger.info(f"   🇳🇬 Nigerian filter: {len(passed)}/{len(results)} passed, {len(filtered)} filtered")
        return passed, filtered

    def detect_duplicates(
        self,
        results: List[XRaySearchResult]
    ) -> Tuple[List[XRaySearchResult], List[FilteredResult]]:
        """
        STEP 4: Remove duplicate content

        Uses URL and title similarity to detect duplicates

        Returns:
            (unique_results, duplicate_results)
        """
        seen_urls = set()
        seen_titles = set()
        unique = []
        duplicates = []

        for result in results:
            url_key = result.url.lower().strip()
            title_key = result.title.lower().strip()

            # Check for duplicate URL or very similar title
            if url_key in seen_urls:
                duplicates.append(FilteredResult(
                    result=result,
                    filter_reason=FilterReasonEnum.DUPLICATE,
                    filter_detail=f"Duplicate URL: {result.url}"
                ))
            elif title_key in seen_titles and len(title_key) > 20:  # Only check title if substantial
                duplicates.append(FilteredResult(
                    result=result,
                    filter_reason=FilterReasonEnum.DUPLICATE,
                    filter_detail=f"Duplicate title: {result.title}"
                ))
            else:
                unique.append(result)
                seen_urls.add(url_key)
                seen_titles.add(title_key)

        logger.info(f"   🔄 Duplicate detection: {len(unique)}/{len(results)} unique, {len(duplicates)} duplicates")
        return unique, duplicates

    # ========================================
    # LLM CLASSIFICATION
    # ========================================

    async def classify_buyer_vs_seller(
        self,
        result: XRaySearchResult
    ) -> BuyerSellerClassification:
        """
        STEP 5: LLM Buyer/Seller Classification (The "LLM Sanitizer")

        Uses OpenAI to distinguish:
        - BUYER: Someone needing a product/service (GOLD)
        - SELLER: Someone advertising/promoting (TRASH)

        This is the critical filter - most Google results are SELLERS
        """

        # Build prompt
        prompt = f"""I will give you a search result.

Is this a BUYER (someone needing a product) or a SELLER (someone advertising)?

If it is a SELLER, return classification: "seller".
If it is a BUYER, return classification: "buyer" and extract their pain point and product needed.

CRITICAL RULES:
- "I sell X" = SELLER
- "Buy my X" = SELLER
- "Looking for X" = BUYER
- "Need help with X" = BUYER
- "Recommend X" = BUYER
- "Problem with X" = BUYER

Search Result:
Title: {result.title}
Description: {result.snippet}
URL: {result.url}

Analyze and respond with the classification.
"""

        try:
            # Call OpenAI with structured output
            classification_result = await self.ai_service.analyze_with_structured_output(
                prompt=prompt,
                response_model=BuyerSellerAnalysisResult,
                model="gpt-4o-mini"  # Use mini for cost savings
            )

            # Map string to enum
            classification_enum = BuyerSellerEnum.UNKNOWN
            if classification_result.classification.lower() == "buyer":
                classification_enum = BuyerSellerEnum.BUYER
            elif classification_result.classification.lower() == "seller":
                classification_enum = BuyerSellerEnum.SELLER

            return BuyerSellerClassification(
                classification=classification_enum,
                confidence=classification_result.confidence,
                reasoning=classification_result.reasoning,
                pain_point=classification_result.pain_point,
                product_needed=classification_result.product_needed
            )

        except Exception as e:
            logger.error(f"   ❌ Error classifying buyer/seller: {str(e)}")
            # Default to unknown on error
            return BuyerSellerClassification(
                classification=BuyerSellerEnum.UNKNOWN,
                confidence=0.0,
                reasoning=f"Error during classification: {str(e)}",
                pain_point=None,
                product_needed=None
            )

    # ========================================
    # FULL PIPELINE
    # ========================================

    async def refine_signals(
        self,
        results: List[XRaySearchResult],
        user_id: str,
        search_keyword: str,
        location: str,
        enable_buyer_seller_classification: bool = True,
        enable_nigerian_filter: bool = True
    ) -> Tuple[List[XRayLead], List[FilteredResult], RefineryMetrics]:
        """
        Run full refinery pipeline

        Returns:
            (leads, filtered_results, metrics)
        """
        start_time = datetime.utcnow()
        logger.info(f"🏭 Starting Signal Refinery pipeline")
        logger.info(f"   Input: {len(results)} raw results")

        total_fetched = len(results)
        all_filtered = []

        # STEP 1: Blocklist
        results, filtered = self.apply_blocklist_filter(results)
        all_filtered.extend(filtered)
        blocklist_filtered_count = len(filtered)

        # STEP 2: Bot patterns
        results, filtered = self.apply_bot_pattern_filter(results)
        all_filtered.extend(filtered)
        bot_filtered_count = len(filtered)

        # STEP 3: Nigerian entity check
        results, filtered = self.apply_nigerian_entity_filter(results, enable_nigerian_filter)
        all_filtered.extend(filtered)
        nigerian_filtered_count = len(filtered)

        # STEP 4: Duplicates
        results, filtered = self.detect_duplicates(results)
        all_filtered.extend(filtered)
        duplicate_filtered_count = len(filtered)

        logger.info(f"   After pre-filtering: {len(results)} results remain")

        # STEP 5: LLM Buyer/Seller Classification
        leads = []
        seller_filtered_count = 0
        llm_cost = 0.0

        if enable_buyer_seller_classification and results:
            logger.info(f"   🤖 Running LLM buyer/seller classification on {len(results)} results...")

            for idx, result in enumerate(results):
                logger.info(f"      [{idx+1}/{len(results)}] Classifying: {result.title[:50]}...")

                classification = await self.classify_buyer_vs_seller(result)

                # Estimate cost (gpt-4o-mini: ~$0.0001 per classification)
                llm_cost += 0.0001

                if classification.classification == BuyerSellerEnum.BUYER:
                    # ✅ BUYER - Create lead
                    lead = XRayLead(
                        user_id=user_id,
                        platform=result.platform,
                        title=result.title,
                        snippet=result.snippet,
                        url=result.url,
                        search_keyword=search_keyword,
                        location=location,
                        dork_query=result.dork_query,
                        buyer_seller=classification,
                        google_rank=result.google_rank,
                        passed_blocklist=True,
                        passed_bot_detection=True,
                        passed_nigerian_check=True
                    )
                    leads.append(lead)
                    logger.info(f"         ✅ BUYER - {classification.product_needed}")

                elif classification.classification == BuyerSellerEnum.SELLER:
                    # ❌ SELLER - Filter out
                    all_filtered.append(FilteredResult(
                        result=result,
                        filter_reason=FilterReasonEnum.SELLER,
                        filter_detail=f"LLM classified as SELLER: {classification.reasoning}"
                    ))
                    seller_filtered_count += 1
                    logger.info(f"         ❌ SELLER - {classification.reasoning[:50]}")

                else:
                    # ⚠️ UNKNOWN - Be conservative, filter out
                    all_filtered.append(FilteredResult(
                        result=result,
                        filter_reason=FilterReasonEnum.NO_INTENT,
                        filter_detail="LLM could not determine buyer/seller"
                    ))
                    logger.info(f"         ⚠️ UNKNOWN")

        else:
            # Skip LLM classification - convert all remaining results to leads
            logger.info(f"   ⏭️ Skipping LLM classification (disabled)")
            for result in results:
                lead = XRayLead(
                    user_id=user_id,
                    platform=result.platform,
                    title=result.title,
                    snippet=result.snippet,
                    url=result.url,
                    search_keyword=search_keyword,
                    location=location,
                    dork_query=result.dork_query,
                    buyer_seller=BuyerSellerClassification(
                        classification=BuyerSellerEnum.UNKNOWN,
                        confidence=0.0,
                        reasoning="LLM classification disabled"
                    ),
                    google_rank=result.google_rank
                )
                leads.append(lead)

        # Calculate metrics
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()

        # Estimate Google search cost ($0.002 per query for apidojo actor)
        # Assuming results came from 1-3 queries depending on volume
        num_queries = max(1, total_fetched // 50)
        google_cost = num_queries * 0.002

        total_cost = google_cost + llm_cost
        cost_per_lead = total_cost / len(leads) if leads else 0.0

        buyer_seller_ratio = len(leads) / total_fetched if total_fetched > 0 else 0.0
        spam_ratio = len(all_filtered) / total_fetched if total_fetched > 0 else 0.0

        metrics = RefineryMetrics(
            total_fetched=total_fetched,
            blocklist_filtered=blocklist_filtered_count,
            bot_filtered=bot_filtered_count,
            nigerian_filtered=nigerian_filtered_count,
            seller_filtered=seller_filtered_count,
            duplicate_filtered=duplicate_filtered_count,
            final_buyer_count=len(leads),
            buyer_seller_ratio=buyer_seller_ratio,
            spam_ratio=spam_ratio,
            google_search_cost=google_cost,
            llm_classification_cost=llm_cost,
            total_cost=total_cost,
            cost_per_lead=cost_per_lead,
            total_time_seconds=total_time,
            leads_per_second=len(leads) / total_time if total_time > 0 else 0.0
        )

        logger.info(f"✅ Refinery pipeline complete!")
        logger.info(f"   📊 Results: {len(leads)} buyers from {total_fetched} raw results")
        logger.info(f"   💰 Cost: ${total_cost:.4f} (${cost_per_lead:.4f} per lead)")
        logger.info(f"   ⏱️ Time: {total_time:.2f}s")

        return leads, all_filtered, metrics
