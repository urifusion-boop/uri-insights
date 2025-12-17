import asyncio
from fastapi import FastAPI, Depends, HTTPException
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from app.database import get_db
from app.core.config import settings
from app.database import connect_to_mongo
from app.core.sentry_config import initialize_sentry

# Initialize Sentry first before anything else
initialize_sentry()
from app.routers import (
    apollo,
    lead_form_snapshots,
    lead_forms,
    nli,
    report_generation,
    uri_ai,
    knowledge,
    bot_agent,
    service_health,
    instagram_insights,
    google_insights,
    linkedin_insights,
    linkedin_campaigns,
    linkedin_shares,
    trackers,
    influencer,
    sentiment,
    tiktok_insights,
    twitter_insights,
    twitter_media,
    twitter_monitoring,
    mention_insights,
    facebook_insights,
    lead_insights,
    reddit_insights,
    facebook_page,
    keyword,
    hashtag,
    social_media_post,
    assistant,
    ai_thread,
    ai_message,
    ai_run,
    webhook,
    openai_apify_twitter,
    openai_apify_tiktok,
    openai_apify_facebook,
    lead_search_history,
    websockets_leads,
)
from app.core.auth_bearer import JWTBearer
from app.core.handlers.exception_handler import global_exception_handler
from app.services.BackgroundService import BackgroundService
from app.core.cache.manager.cache_manager import CacheManager  # 🔹 Import CacheManager
from app.core.managers.ProcessPoolManager import process_pool_manager
from app.core.managers.ThreadPoolManager import thread_pool_manager
from app.lifecycle_tasks import (
    shutdown_service_bus_consumers,
    start_service_bus_consumers,
    run_db_startup_tasks,
)


class APIInfo(BaseModel):
    title: str = "URI Insights API"
    swagger: str = "v1"
    description: str = "API documentation for URI Insights"
    version: str = "v1"
    contact: dict = {"name": "Uri Fusion", "email": "urifusion@gmail.com"}
    license_info: dict = {"name": "MIT License"}


app = FastAPI(
    title=APIInfo().title,
    description=APIInfo().description,
    version=APIInfo().version,
    contact=APIInfo().contact,
    license_info=APIInfo().license_info,
    docs_url=None,  # Disable the default docs
    redoc_url=None,
    openapi_tags=[
        {
            "name": "auth",
            "description": "Operations with authentication",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.exception_handler(HTTPException)
def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.add_exception_handler(Exception, global_exception_handler)
connect_to_mongo(settings.MONGODB_DB)

CacheManager.initialize()  # ✅ Cache initialized globally here
# APScheduler integration
scheduler = BackgroundService.start_scheduler(get_db())

consumer_tasks: list[asyncio.Task] = []


@app.on_event("startup")
async def start_consumer():
    await run_db_startup_tasks()
    await start_service_bus_consumers()


@app.on_event("shutdown")
async def shutdown_event():
    """
    Ensure the scheduler is shut down properly during application shutdown.
    """
    scheduler.shutdown()
    process_pool_manager.shutdown()
    thread_pool_manager.shutdown()
    await shutdown_service_bus_consumers()


app.include_router(
    uri_ai.router,
    prefix="/openai",
    tags=["openai"],
    dependencies=[Depends(JWTBearer())],
)

app.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(JWTBearer())],
)
app.include_router(
    bot_agent.router,
    prefix="/bot-agent",
    tags=["live agent"],
    dependencies=[Depends(JWTBearer())],
)
app.include_router(
    service_health.router,
    prefix="",
    tags=["service-health"],
)
app.include_router(
    instagram_insights.router,
    prefix="/instagram",
    tags=["instagram"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    google_insights.router,
    prefix="/google",
    tags=["google"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    trackers.router,
    prefix="/keyword",
    tags=["keyword"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    keyword.router,
    prefix="/keyword",
    tags=["Keyword Tracking"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    hashtag.router,
    prefix="/hashtag",
    tags=["Hashtag Tracking"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    lead_insights.router,
    prefix="/lead",
    tags=["Lead Tracking"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    reddit_insights.router,
    prefix="/reddit",
    tags=["reddit"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    social_media_post.router,
    prefix="/social-media-post",
    tags=["Social Media Post"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    influencer.router,
    prefix="/influencer",
    tags=["influencer"],
    dependencies=[Depends(JWTBearer())],
)

app.include_router(
    facebook_page.router,
    prefix="/facebook-page",
    tags=["Facebook Page"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    linkedin_campaigns.router,
    prefix="/linkedin-campaigns",
    tags=["LinkedIn Campaigns"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    linkedin_insights.router,
    prefix="/linkedin-insights",
    tags=["LinkedIn Insights"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    linkedin_shares.router,
    prefix="/linkedin-shares",
    tags=["LinkedIn Shares"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    tiktok_insights.router,
    prefix="/tiktok-insights",
    tags=["Tiktok Insights"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    twitter_insights.router,
    prefix="/x-insights",
    tags=["X Insights"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    mention_insights.router,
    prefix="/mention-insights",
    tags=["Mention Insights"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    twitter_media.router,
    prefix="/x-media",
    tags=["X Media"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    twitter_monitoring.router,
    prefix="/twitter-monitoring",
    tags=["Twitter Monitoring (Playwright)"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    facebook_insights.router,
    prefix="/facebook-insights",
    tags=["Facebook Insights"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    sentiment.router,
    prefix="/sentiment",
    tags=["Sentiment Analysis"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    assistant.router,
    prefix="/assistant",
    tags=["AI Assistant"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    ai_thread.router,
    prefix="/ai-thread",
    tags=["AI Assistant Thread"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    ai_message.router,
    prefix="/ai-message",
    tags=["AI Messaging"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    ai_run.router,
    prefix="/ai-run",
    tags=["AI Run"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    report_generation.router,
    prefix="/report",
    tags=["Report Generation"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    lead_forms.router,
    prefix="/lead-forms",
    tags=["Lead Forms"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    lead_form_snapshots.router,
    prefix="/lead-form-snapshots",
    tags=["Lead Form Snapshots"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    apollo.router,
    prefix="/apollo",
    tags=["Apollo"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    nli.router,
    prefix="/natural-language-interface",
    tags=["Natural Language Interface"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    webhook.router,
    prefix="/webhooks",
)

app.include_router(
    openai_apify_twitter.router,
    prefix="/openai-apify-twitter",
    tags=["OpenAI Apify Twitter Integration"],
)
app.include_router(
    openai_apify_tiktok.router,
    prefix="/openai-apify-tiktok",
    tags=["OpenAI Apify TikTok Integration"],
)
app.include_router(
    openai_apify_facebook.router,
    prefix="/openai-apify-facebook",
    tags=["OpenAI Apify Facebook Integration"],
)

app.include_router(
    lead_search_history.router,
    prefix="/api/v1",
    tags=["Lead Search History"],
    dependencies=[Depends(JWTBearer(validate_subscription=True))],
)

app.include_router(
    websockets_leads.router,
    prefix="",
    tags=["WebSocket Real-time Leads"],
)


@app.get("/")
def read_root() -> dict:
    return {"message": "Welcome to URI Insights API"}


@app.get("/swagger", include_in_schema=False)
async def custom_swagger_ui_html() -> Any:
    return get_swagger_ui_html(
        openapi_url="/swagger/v1/swagger.json", title=app.title + " - Swagger UI"
    )


@app.get("/swagger/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect() -> Any:
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/swagger/v1/swagger.json", include_in_schema=False)
async def openapi_schema() -> Any:
    return app.openapi()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    # Generate the OpenAPI schema
    openapi_schema = app.openapi()

    # Define the Bearer Token and Meta-Access-Token as security schemes in the header
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        "MetaAccessToken": {
            "type": "apiKey",
            "name": "Meta-Access-Token",
            "in": "header",
        },
    }

    # Apply both Bearer token and Meta-Access-Token security globally
    openapi_schema["security"] = [{"BearerAuth": []}, {"MetaAccessToken": []}]

    return openapi_schema


# Run the application with SSL enabled
if __name__ == "__main__":
    import uvicorn

    # if settings.ENV == "Development":
    #     uvicorn.run(app, host="0.0.0.0", port=443)
    # else:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=443,
        ssl_keyfile=settings.SSL_KEY_PATH,  # Path to the private key
        ssl_certfile=settings.SSL_CERT_PATH,  # Path to the certificate
    )
