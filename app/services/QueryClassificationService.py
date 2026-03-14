"""
Query Classification Service

Classifies user search queries to route them to the appropriate data source:
- Structured Company Dataset (Apollo): For registered organizations, startups, tech companies
- Local Business Dataset (Google Maps): For location-based service businesses
- Hybrid: For queries that should search both sources and merge results

Based on: Query Classification & Search Routing Logic PRD
"""

from typing import List, Literal, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass


class QueryRouteType(str, Enum):
    """Types of routing paths for lead searches"""
    STRUCTURED = "STRUCTURED"  # Apollo only
    LOCAL = "LOCAL"  # Google Maps only
    HYBRID = "HYBRID"  # Both Apollo and Google Maps


@dataclass
class QueryClassificationResult:
    """Result of query classification"""
    route_type: QueryRouteType
    business_category: str
    location: Optional[str]
    keywords: List[str]
    confidence: float  # 0.0 to 1.0


class QueryClassificationService:
    """
    Classifies user queries to determine the appropriate search routing.

    Implements the Query Classification & Search Routing Logic from PRD.
    """

    # Structured Company Keywords (Apollo)
    # These represent registered organizations, startups, tech companies, agencies
    STRUCTURED_KEYWORDS = {
        # Company types
        'startup', 'startups', 'company', 'companies', 'firm', 'firms',
        'agency', 'agencies', 'consulting', 'organization', 'organizations',

        # Tech/Software
        'software', 'saas', 'technology', 'tech', 'ai', 'artificial intelligence',
        'blockchain', 'crypto', 'digital', 'platform', 'app', 'application',

        # Industry-specific tech
        'fintech', 'edtech', 'healthtech', 'agritech', 'proptech', 'insuretech',
        'regtech', 'martech', 'cleantech', 'foodtech', 'logistics tech',

        # Professional services
        'consulting firm', 'consultancy', 'marketing agency', 'digital agency',
        'advertising agency', 'creative agency', 'pr agency', 'media agency',
        'logistics company', 'logistics companies', 'supply chain',

        # Corporate descriptors
        'b2b', 'b2c', 'enterprise', 'sme', 'corporation', 'venture-backed',
        'funded', 'series a', 'series b', 'unicorn', 'scaleup',
    }

    # Local Business Keywords (Google Maps)
    # These represent physical, location-based service businesses
    LOCAL_KEYWORDS = {
        # Food & Beverage
        'restaurant', 'restaurants', 'cafe', 'cafes', 'coffee shop', 'coffee shops',
        'bar', 'bars', 'pub', 'pubs', 'club', 'clubs', 'nightclub', 'nightclubs',
        'eatery', 'eateries', 'bakery', 'bakeries', 'fast food', 'food court',

        # Personal Care
        'salon', 'salons', 'barbershop', 'barbershops', 'barber', 'barbers',
        'beauty salon', 'hair salon', 'spa', 'spas', 'nail salon', 'massage',

        # Retail
        'supermarket', 'supermarkets', 'store', 'stores', 'shop', 'shops',
        'market', 'markets', 'boutique', 'boutiques', 'mall', 'shopping center',

        # Fitness & Wellness
        'gym', 'gyms', 'fitness center', 'fitness', 'yoga studio', 'pilates',

        # Hospitality
        'hotel', 'hotels', 'motel', 'motels', 'guest house', 'lodge', 'lodges',

        # Services
        'coworking space', 'coworking spaces', 'co-working', 'workspace',
        'workshop', 'workshops', 'repair shop', 'repair shops',
        'auto repair', 'car repair', 'car wash', 'mechanic', 'garage',
        'laundry', 'laundromat', 'laundromats', 'dry cleaning',
        'printing shop', 'print shop', 'copy center',

        # Financial Services (local)
        'pos agent', 'pos agents', 'mobile money agent', 'mobile money agents',
        'money transfer', 'bureau de change', 'forex bureau',

        # Healthcare (local facilities)
        'pharmacy', 'pharmacies', 'chemist', 'clinic', 'clinics',
        'medical center', 'diagnostic center',

        # Other local services
        'event venue', 'event venues', 'photo studio', 'photography studio',
    }

    # Hybrid Keywords (Both Apollo and Google Maps)
    # These can exist as both corporate entities and local offices/branches
    HYBRID_KEYWORDS = {
        # Healthcare institutions
        'hospital', 'hospitals', 'medical', 'healthcare',

        # Education
        'school', 'schools', 'university', 'universities', 'college', 'colleges',
        'training institute', 'training institutes', 'academy', 'academies',
        'learning center', 'education center',

        # Professional services (can be both corporate HQ and local branches)
        'law firm', 'law firms', 'legal', 'lawyer', 'lawyers', 'attorney',
        'accounting firm', 'accounting firms', 'audit firm', 'accountant',
        'consulting company', 'consulting companies',

        # Financial institutions
        'bank', 'banks', 'insurance company', 'insurance companies',
        'microfinance', 'financial institution', 'financial services',

        # Real estate
        'real estate', 'real estate company', 'real estate companies',
        'property', 'property company', 'property management',

        # Construction
        'construction company', 'construction companies', 'contractor',
        'contractors', 'building company', 'engineering firm',

        # Recruitment
        'recruitment agency', 'recruitment agencies', 'staffing agency',
        'hr consultancy', 'talent acquisition',
    }

    @classmethod
    def classify_query(
        cls,
        user_prompt: str,
        lead_form_keywords: Optional[List[str]] = None,
        organization_keywords: Optional[List[str]] = None
    ) -> QueryClassificationResult:
        """
        Classify a user query to determine the appropriate routing path.

        Args:
            user_prompt: The user's search query (e.g., "Find fintechs in Lagos")
            lead_form_keywords: Keywords from lead form q_organization_keyword_tags
            organization_keywords: Additional organization-specific keywords

        Returns:
            QueryClassificationResult with route type and extracted information
        """
        prompt_lower = user_prompt.lower()

        # Extract keywords from the query
        all_keywords = cls._extract_keywords(
            prompt_lower, lead_form_keywords, organization_keywords
        )

        # Extract location (pass original prompt to preserve capitalization)
        location = cls._extract_location(user_prompt, prompt_lower)

        # Step 1: Check for HYBRID keywords (highest priority)
        # These queries should search both Apollo and Google Maps
        hybrid_matches = cls._find_keyword_matches(all_keywords, cls.HYBRID_KEYWORDS)
        if hybrid_matches:
            return QueryClassificationResult(
                route_type=QueryRouteType.HYBRID,
                business_category=hybrid_matches[0],
                location=location,
                keywords=all_keywords,
                confidence=0.9
            )

        # Step 2: Check for STRUCTURED keywords
        # These are sector-based company searches (Apollo only)
        structured_matches = cls._find_keyword_matches(all_keywords, cls.STRUCTURED_KEYWORDS)
        if structured_matches:
            return QueryClassificationResult(
                route_type=QueryRouteType.STRUCTURED,
                business_category=structured_matches[0],
                location=location,
                keywords=all_keywords,
                confidence=0.85
            )

        # Step 3: Check for LOCAL keywords
        # These are location-based service businesses (Google Maps only)
        local_matches = cls._find_keyword_matches(all_keywords, cls.LOCAL_KEYWORDS)
        if local_matches:
            return QueryClassificationResult(
                route_type=QueryRouteType.LOCAL,
                business_category=local_matches[0],
                location=location,
                keywords=all_keywords,
                confidence=0.85
            )

        # Step 4: Default to STRUCTURED for generic company searches
        # If no specific keywords found, assume it's a general company search
        return QueryClassificationResult(
            route_type=QueryRouteType.STRUCTURED,
            business_category="business",
            location=location,
            keywords=all_keywords,
            confidence=0.5
        )

    @classmethod
    def _extract_keywords(
        cls,
        prompt: str,
        lead_form_keywords: Optional[List[str]] = None,
        organization_keywords: Optional[List[str]] = None
    ) -> List[str]:
        """Extract and combine all relevant keywords from query and lead form"""
        keywords = []

        # Add keywords from lead form
        if lead_form_keywords:
            keywords.extend([k.lower() for k in lead_form_keywords])

        if organization_keywords:
            keywords.extend([k.lower() for k in organization_keywords])

        # Extract significant words from prompt (filter out common words)
        stop_words = {
            'find', 'search', 'get', 'looking', 'for', 'in', 'at', 'the', 'a', 'an',
            'and', 'or', 'of', 'to', 'from', 'with', 'by', 'on', 'near', 'around'
        }
        prompt_words = [
            word for word in prompt.split()
            if word not in stop_words and len(word) > 2
        ]
        keywords.extend(prompt_words)

        return list(set(keywords))  # Remove duplicates

    @classmethod
    def _find_keyword_matches(
        cls,
        query_keywords: List[str],
        category_keywords: set
    ) -> List[str]:
        """Find matching keywords between query and category"""
        import re
        matches = []
        query_text = " ".join(query_keywords)

        for keyword in category_keywords:
            # Check for exact word match in keywords list
            if keyword in query_keywords:
                matches.append(keyword)
                continue

            # For multi-word keywords, check if the phrase exists with word boundaries
            # This prevents "ai" from matching "nairobi"
            if " " in keyword:
                # Multi-word phrase - check if it exists in query text
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_text):
                    matches.append(keyword)
                    continue

                # Also check if all parts are present (handles "real estate company" vs "real estate companies")
                keyword_parts = keyword.split()
                if all(part in query_text for part in keyword_parts):
                    matches.append(keyword)
            else:
                # Single-word keyword - require word boundaries
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_text):
                    matches.append(keyword)

        return matches

    @classmethod
    def _extract_location(cls, original_prompt: str, prompt_lower: str) -> Optional[str]:
        """
        Extract location from query.

        Common patterns:
        - "Find X in Lagos"
        - "Find X near Nairobi"
        - "Find Lagos startups"
        - "Find Accra restaurants"

        Args:
            original_prompt: Original prompt with proper capitalization
            prompt_lower: Lowercased version for pattern matching

        Returns:
            Location string with proper capitalization
        """
        # Common location prepositions
        location_indicators = ['in', 'near', 'around', 'at']

        words_lower = prompt_lower.split()
        words_original = original_prompt.split()

        for i, word in enumerate(words_lower):
            if word in location_indicators and i + 1 < len(words_original):
                # Return the word(s) after the location indicator from original prompt
                # Handle multi-word locations like "Port Harcourt"
                location_parts = []
                for j in range(i + 1, min(i + 4, len(words_original))):  # Max 3 words for location
                    next_word_lower = words_lower[j] if j < len(words_lower) else ''
                    # Stop at common words that aren't part of location
                    if next_word_lower in ['with', 'that', 'which', 'having', 'for']:
                        break
                    location_parts.append(words_original[j])

                if location_parts:
                    return " ".join(location_parts).strip(',.')

        # Check for location at the end of prompt without location indicator
        # e.g., "restaurants Accra" or "startups Lagos"
        if len(words_original) >= 2:
            last_word = words_original[-1].strip(',.')
            last_word_lower = words_lower[-1].strip(',.')
            # Check if it's not a keyword (likely a location)
            if (last_word_lower not in cls.STRUCTURED_KEYWORDS and
                last_word_lower not in cls.LOCAL_KEYWORDS and
                last_word_lower not in cls.HYBRID_KEYWORDS):
                return last_word

        return None

    @classmethod
    def should_use_apollo(cls, route_type: QueryRouteType) -> bool:
        """Check if Apollo should be queried for this route type"""
        return route_type in [QueryRouteType.STRUCTURED, QueryRouteType.HYBRID]

    @classmethod
    def should_use_google_maps(cls, route_type: QueryRouteType) -> bool:
        """Check if Google Maps should be queried for this route type"""
        return route_type in [QueryRouteType.LOCAL, QueryRouteType.HYBRID]

    @classmethod
    def get_search_strategy(cls, classification: QueryClassificationResult) -> Dict[str, Any]:
        """
        Get the complete search strategy based on classification.

        Returns a dictionary with:
        - use_apollo: bool
        - use_google_maps: bool
        - apollo_mode: 'primary' | 'enrichment' | None
        - google_maps_mode: 'primary' | 'fallback' | 'enrichment' | None
        - merge_results: bool
        """
        route_type = classification.route_type

        if route_type == QueryRouteType.STRUCTURED:
            return {
                "use_apollo": True,
                "use_google_maps": False,
                "apollo_mode": "primary",
                "google_maps_mode": None,
                "merge_results": False,
                "description": "Apollo-only search for structured companies"
            }

        elif route_type == QueryRouteType.LOCAL:
            return {
                "use_apollo": False,
                "use_google_maps": True,
                "apollo_mode": None,
                "google_maps_mode": "primary",
                "merge_results": False,
                "description": "Google Maps-only search for local businesses"
            }

        else:  # HYBRID
            return {
                "use_apollo": True,
                "use_google_maps": True,
                "apollo_mode": "primary",
                "google_maps_mode": "fallback",
                "merge_results": True,
                "description": "Hybrid search - Apollo first, Google Maps fallback, merge results"
            }
