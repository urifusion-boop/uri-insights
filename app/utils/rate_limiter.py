"""
Rate Limiter Utility
Prevents API rate limit violations for HubSpot and Salesforce

HubSpot Limits:
- 100 requests per 10 seconds (per access token)
- 150,000 requests per day

Salesforce Limits:
- Varies by license type (typically 15,000-100,000 per day)
- No per-second limit, but best practice is to pace requests
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import deque


class RateLimiter:
    """
    Token bucket rate limiter for API calls

    Implements sliding window rate limiting to prevent API throttling
    """

    def __init__(self, max_requests: int, time_window_seconds: int):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum number of requests allowed in time window
            time_window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = timedelta(seconds=time_window_seconds)
        self.requests: deque = deque()  # Store timestamps of recent requests
        self.lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquire permission to make an API call
        Blocks until rate limit allows the request
        """
        async with self.lock:
            now = datetime.utcnow()

            # Remove requests outside the time window
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()

            # If at limit, wait until oldest request expires
            if len(self.requests) >= self.max_requests:
                oldest_request = self.requests[0]
                wait_until = oldest_request + self.time_window
                sleep_duration = (wait_until - now).total_seconds()

                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

                # Remove expired request
                self.requests.popleft()

            # Record this request
            self.requests.append(datetime.utcnow())

    def get_current_usage(self) -> Dict[str, any]:
        """
        Get current rate limit usage stats

        Returns:
            Dictionary with current usage information
        """
        now = datetime.utcnow()

        # Remove expired requests
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()

        return {
            "current_requests": len(self.requests),
            "max_requests": self.max_requests,
            "time_window_seconds": self.time_window.total_seconds(),
            "requests_remaining": self.max_requests - len(self.requests),
            "usage_percentage": (len(self.requests) / self.max_requests) * 100 if self.max_requests > 0 else 0,
        }


class HubSpotRateLimiter(RateLimiter):
    """
    Rate limiter specifically for HubSpot API
    Limit: 100 requests per 10 seconds
    """

    def __init__(self):
        # Use 95 requests per 10 seconds to leave buffer
        super().__init__(max_requests=95, time_window_seconds=10)


class SalesforceRateLimiter(RateLimiter):
    """
    Rate limiter for Salesforce API
    Conservative limit: 100 requests per 20 seconds (safe for most licenses)
    """

    def __init__(self):
        super().__init__(max_requests=100, time_window_seconds=20)


# Global rate limiter instances (singleton pattern)
_hubspot_limiter: Optional[HubSpotRateLimiter] = None
_salesforce_limiter: Optional[SalesforceRateLimiter] = None


def get_hubspot_rate_limiter() -> HubSpotRateLimiter:
    """Get or create HubSpot rate limiter instance"""
    global _hubspot_limiter
    if _hubspot_limiter is None:
        _hubspot_limiter = HubSpotRateLimiter()
    return _hubspot_limiter


def get_salesforce_rate_limiter() -> SalesforceRateLimiter:
    """Get or create Salesforce rate limiter instance"""
    global _salesforce_limiter
    if _salesforce_limiter is None:
        _salesforce_limiter = SalesforceRateLimiter()
    return _salesforce_limiter
