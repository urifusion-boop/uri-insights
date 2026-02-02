"""
Sentry configuration for uri-insights service
Integrates Sentry for error tracking while maintaining Azure Service Bus logging for dashboard
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
import os


def initialize_sentry():
    """
    Initialize Sentry with FastAPI and PyMongo integrations
    This will send exceptions to Sentry for tracking AND to Azure Service Bus for dashboard
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        print("[Sentry] SENTRY_DSN not found in environment, skipping initialization")
        return

    environment = os.getenv("ENV", "Development")

    sentry_sdk.init(
        dsn=sentry_dsn,
        # Add data like request headers and IP for users
        send_default_pii=True,
        # Set environment
        environment=environment,
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for tracing
        traces_sample_rate=1.0,
        # To collect profiles for all profile sessions, set profile_session_sample_rate to 1.0
        profile_session_sample_rate=1.0,
        # Profiles will be automatically collected while there is an active span
        profile_lifecycle="trace",
        # Enable logs to be sent to Sentry
        enable_logs=True,
        # Integrations
        integrations=[
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={*range(500, 599)},
                http_methods_to_capture=("GET", "POST", "PUT", "DELETE", "PATCH"),
            ),
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={*range(500, 599)},
                http_methods_to_capture=("GET", "POST", "PUT", "DELETE", "PATCH"),
            ),
            PyMongoIntegration(),
        ],
    )

    # Set tags for better filtering in Sentry
    sentry_sdk.set_tag("service", "uri-insights")
    sentry_sdk.set_tag("service_type", "python-fastapi")

    print(f"[Sentry] Initialized successfully for uri-insights (env: {environment})")
