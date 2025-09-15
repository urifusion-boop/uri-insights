import requests
from app.core.config import settings
from typing import Any, Dict


class MetaService:
    @staticmethod
    def fetch_meta_data(query: str) -> Any:
        api_key = ""
        url = f"https://graph.facebook.com/v9.0/{query}?access_token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
