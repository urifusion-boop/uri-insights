from typing import Any


class LeadDataScraper:
    async def scrape(self, db, params: Any):
        raise NotImplementedError("Subclasses must implement this method")
