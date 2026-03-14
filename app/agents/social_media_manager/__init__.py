# app/agents/social_media_manager/__init__.py

"""
URI Social Media Manager Agent

This agent transforms URI from a social listening platform into a complete 
AI-powered social media management system.

Features:
- Multi-platform content generation (LinkedIn, Twitter, Facebook, Instagram)
- Platform-native AI prompts optimized for Nigerian business context
- Outstand integration for unified multi-platform publishing
- Content approval workflows
- Performance analytics and insights
- Integration with existing social listening (Lazarus Protocol)

Author: URI Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "URI Development Team"

from .services.outstand_service import OutstandService
from .services.content_generation_service import ContentGenerationService

__all__ = [
    "OutstandService",
    "ContentGenerationService"
]