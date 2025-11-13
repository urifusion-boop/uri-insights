"""
Configuration for AI-powered lead filtering
"""

from enum import Enum


class LeadFilterThresholds(Enum):
    """Relevance score thresholds for different lead types"""
    
    # Conversational/Business leads (from social media)
    # Higher threshold since there's more noise
    CONVERSATIONAL = 0.65
    
    # Apollo Person leads (from professional databases)
    # Lower threshold since data is already pre-qualified
    PERSON = 0.50
    
    # Apollo Organization leads (from business databases)
    # Lower threshold since targeting is already precise
    ORGANIZATION = 0.50
    
    # Real-time monitoring leads
    # Medium threshold for real-time alerts
    REALTIME = 0.60


class IntentWeights(Enum):
    """Weight distribution for scoring calculation"""
    
    # Semantic similarity weight (keyword matching via embeddings)
    SEMANTIC = 0.30
    
    # AI intent analysis weight (GPT-4 deep understanding)
    INTENT = 0.70


class LeadFilterSettings:
    """
    Global settings for AI lead filtering.
    These can be overridden per lead form or user preference.
    """
    
    # Enable/disable AI filtering globally
    ENABLED = True
    
    # Minimum semantic similarity score before running expensive GPT analysis
    SEMANTIC_PREFILTER_THRESHOLD = 0.40
    
    # Embedding model for semantic matching
    EMBEDDING_MODEL = "text-embedding-3-small"
    
    # GPT model for intent analysis
    INTENT_ANALYSIS_MODEL = "gpt-4o-mini"
    
    # Maximum leads to process in a single batch
    MAX_BATCH_SIZE = 50
    
    # Cache embeddings to reduce API calls
    ENABLE_EMBEDDING_CACHE = True
    
    # Temperature for GPT intent analysis (lower = more consistent)
    INTENT_ANALYSIS_TEMPERATURE = 0.3
    
    # Auto-generate follow-up messages for high-score leads only
    AUTO_FOLLOWUP_THRESHOLD = 0.75
    
    # Intent types that should use stricter filtering
    STRICT_INTENT_TYPES = ["sales", "partnership"]
    
    # Intent types that should use relaxed filtering
    RELAXED_INTENT_TYPES = ["research", "marketing"]
    
    @staticmethod
    def get_threshold_for_lead_type(lead_type: str, intent_type: str = None) -> float:
        """
        Get the appropriate threshold based on lead type and intent.
        
        Args:
            lead_type: Type of lead form (CONVERSATIONAL, PERSON, ORGANIZATION)
            intent_type: User's intent (sales, hiring, partnership, etc.)
            
        Returns:
            Relevance score threshold (0.0-1.0)
        """
        base_threshold = getattr(
            LeadFilterThresholds, 
            lead_type.upper(), 
            LeadFilterThresholds.CONVERSATIONAL
        ).value
        
        # Adjust threshold based on intent type
        if intent_type in LeadFilterSettings.STRICT_INTENT_TYPES:
            return min(base_threshold + 0.05, 0.95)  # Stricter
        elif intent_type in LeadFilterSettings.RELAXED_INTENT_TYPES:
            return max(base_threshold - 0.10, 0.30)  # More relaxed
        
        return base_threshold
