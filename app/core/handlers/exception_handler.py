from datetime import datetime
import traceback
from fastapi import Request, HTTPException
import requests
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
import sentry_sdk
from app.core.helpers.middleware_helper import MiddlewareHelper
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.microservicestype_enum import MicroServiceTypeEnum
from app.domain.responses.uri_response import UriResponse
from app.middlewares.FeatureLimitMiddleware import FeatureLimitExceeded
from app.services.azure.producers.ExceptionLogProducer import (
    ExceptionLogQueueProducerService,
)


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that sends exceptions to:
    1. Sentry - for error tracking and monitoring
    2. Azure Service Bus - for custom dashboard display
    """
    print(f"Global exception handler triggered for: {exc}")

    try:
        user_id = MiddlewareHelper.get_user_id(request)
    except:
        user_id = "SYSTEM"

    full_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Determine status code
    status_code = 500
    if isinstance(exc, HTTPException):
        status_code = exc.status_code

    # 1. Send to Sentry for error tracking
    with sentry_sdk.push_scope() as scope:
        scope.set_context("http", {
            "method": request.method,
            "url": str(request.url),
            "user_id": user_id,
        })
        scope.set_tag("service", "uri-insights")
        scope.set_tag("endpoint", request.url.path)
        scope.set_tag("user_id", user_id)
        scope.set_level("error")

        sentry_sdk.capture_exception(exc)

    # 2. Send to Azure Service Bus for dashboard
    log_data = {
        "userId": user_id,
        "exceptionDate": DateHelper.utc_now_iso(),
        "method": request.method,
        "url": request.url.path,
        "status": status_code,
        "exception": full_trace,
        "serviceType": MicroServiceTypeEnum.URI_INSIGHTS.value,
    }

    await ExceptionLogQueueProducerService.publish_exception_log(
        exception_data=log_data,
    )

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        if exc.status_code == 401 or exc.status_code == 403:
            status_code = 400
        return JSONResponse(status_code=status_code, content={"message": exc.detail})
    elif isinstance(exc, requests.HTTPError) and exc.response.status_code == 429:
        return JSONResponse(
            status_code=429,
            content=UriResponse.custom_response(
                "Too many requests, try again later, much later.", 429
            ),
        )
    elif isinstance(exc, FeatureLimitExceeded):
        return JSONResponse(
            status_code=403,
            content={
                "message": str(exc),
                "limit_exceeded": True,
                "error_code": 403
            },
        )
    else:
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=UriResponse.error_response(str(exc)),
        )
