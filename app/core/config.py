from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    MONGODB_USER: str = ""
    MONGODB_PASSWORD: str = ""
    MONGODB_HOST: str
    MONGODB_DB: str
    MONGODB_URI: str
    OPENAI_API_KEY: str
    GOOGLE_API_KEY: str
    GOOGLE_CUSTOM_SEARCH_ENGINE_API_KEY: str
    URI_SEARCH_ENGINE_ID: str
    META_API_KEY: str
    META_APP_ID: str
    META_SYSTEM_TOKEN: str
    AUTHJWT_SECRET_KEY: str
    INSTAGRAM_API_VERSION: str
    FACEBOOK_API_VERSION: str
    INSTAGRAM_BUSINESS_ID: str
    TIKTOK_CLIENT_TOKEN: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    X_APP_BEARER_TOKEN: str
    LINKEDIN_VERSION: str
    ENV: str
    DEV_ENV: str
    AZURE_SERVICE_BUS_CONNECTION_STRING: str
    LINKEDIN_PAGES_DISCOVERY_URL: str
    URI_INSTAGRAM_ID: str
    WEBHOOK_VERIFY_TOKEN: str
    LEAD_GENERATION_INTERVAL: int
    LEAD_GENERATION_INTERVAL_MINUTES_FOR_TEST: Optional[int] = None
    KEYWORD_TRACKING_ASSISTANT_ID: str
    CONTENT_MANAGEMENT_ASSISTANT_ID: str
    HASHTAG_TRACKING_ASSISTANT_ID: str
    ACCOUNT_TRACKING_ASSISTANT_ID: str
    LEAD_TRACKING_ASSISTANT_ID: str

    REDDIT_APP_NAME: str
    REDDIT_APP_VERSION: str
    REDDIT_USERNAME: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str

    FIRECRAWL_API_KEY: str

    WEB_APP_URL: str

    URI_TASK_MANAGER_FEATURE_LIMIT: str
    URI_TASK_MANAGER_UPDATE_FEATURE_LIMIT_SPECIFIC_LIMIT: str
    URI_TASK_MANAGER_UPDATE_FEATURE_LIMIT_OBJECT: str
    URI_TASK_MANAGER_CREATE_FEATURE_LIMIT: str
    URI_GATEWAY_BASE_API_URL: str

    URI_BACKEND_BASE_URL: str
    URI_TRANSACTIONS_BASE_URL: str
    URI_TASK_MANAGER_BASE_URL: str
    URI_BACKEND_USER_DETAILS: str
    MAX_TWITTER_POSTS: int
    APOLLO_API_KEY: str
    URI_CLIENT_ID: str
    URI_CLIENT_SECRET: str
    SSL_KEY_PATH: str
    SSL_CERT_PATH: str
    
    # Browsercloud Configuration
    BROWSERCLOUD_API_KEY: str
    BROWSERCLOUD_API_URL: str = "https://api.browsercloud.io"
    BROWSERCLOUD_WEBHOOK_SECRET: str
    BROWSERCLOUD_MAX_CONCURRENT_TASKS: int = 10

    # Twitter Monitoring with Playwright
    TWITTER_USERNAME: str = ""
    TWITTER_PASSWORD: str = ""
    
    # Apify Configuration
    APIFY_API_TOKEN: str = ""
    APIFY_API_TOKEN_BACKUP: str = ""  # Backup token for failover
    APIFY_TIMEOUT_SECONDS: int = 60   # Timeout before switching to backup

    # Gemini Configuration (for LLM fallback)
    GEMINI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields to be ignored


settings = Settings()
