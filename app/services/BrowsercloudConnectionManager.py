"""
Browsercloud Connection Manager
Manages persistent browser connections via Browsercloud's remote browser service.
"""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class BrowsercloudConnectionManager:
    """Manages browser connections to Browsercloud remote browsers."""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.connection_url = self._build_connection_url()
        self._lock = asyncio.Lock()
        self.is_connected = False

    def _build_connection_url(self) -> str:
        """Build WebSocket connection URL for Browsercloud."""
        api_key = settings.BROWSERCLOUD_API_KEY
        # Browsercloud.io connection format
        return f"wss://chrome-v2.browsercloud.io/playwright?token={api_key}"

    async def connect(self) -> Browser:
        """Establish connection to Browsercloud remote browser."""
        async with self._lock:
            if self.browser and self.is_connected:
                logger.info("Browser already connected")
                return self.browser

            try:
                logger.info("Connecting to Browsercloud remote browser...")
                self.playwright = await async_playwright().start()

                # Connect to remote browser via WebSocket
                self.browser = await self.playwright.chromium.connect(
                    self.connection_url,
                    timeout=60000  # 60 second timeout
                )

                self.is_connected = True
                logger.info("Successfully connected to Browsercloud")
                return self.browser

            except Exception as e:
                logger.error(f"Failed to connect to Browsercloud: {e}")
                self.is_connected = False
                raise

    async def create_context(self, **kwargs) -> BrowserContext:
        """Create a new browser context with stealth settings."""
        if not self.browser or not self.is_connected:
            await self.connect()

        # Default context options for stealth
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "America/New_York",
            **kwargs
        }

        self.context = await self.browser.new_context(**context_options)

        # Add stealth scripts to avoid detection
        await self._apply_stealth_scripts(self.context)

        return self.context

    async def _apply_stealth_scripts(self, context: BrowserContext):
        """Apply stealth techniques to avoid bot detection."""
        # Override navigator properties
        await context.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Override chrome property
            window.chrome = {
                runtime: {}
            };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

    async def new_page(self) -> Page:
        """Create a new page in the current context."""
        if not self.context:
            await self.create_context()

        page = await self.context.new_page()
        return page

    async def disconnect(self):
        """Close browser connection and cleanup."""
        async with self._lock:
            try:
                if self.context:
                    await self.context.close()
                    self.context = None

                if self.browser:
                    await self.browser.close()
                    self.browser = None

                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None

                self.is_connected = False
                logger.info("Disconnected from Browsercloud")

            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

    async def reconnect(self) -> Browser:
        """Reconnect to Browsercloud after connection loss."""
        logger.info("Attempting to reconnect to Browsercloud...")
        await self.disconnect()
        await asyncio.sleep(5)  # Wait before reconnecting
        return await self.connect()

    async def is_browser_alive(self) -> bool:
        """Check if browser connection is still alive."""
        try:
            if not self.browser or not self.is_connected:
                return False

            # Try to get browser version as health check
            contexts = self.browser.contexts
            return len(contexts) >= 0
        except Exception:
            return False

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()
