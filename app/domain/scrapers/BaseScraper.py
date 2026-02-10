from typing import Any, Optional

import requests


class BaseScraper:
    def __init__(
        self, url: str, params: Optional[Any] = None, headers: Optional[dict] = None
    ):
        self.url = url
        self.params = params
        self.headers = headers
        self.max_retries = 3

    def fetch_data(self):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                response = requests.get(
                    self.url,
                    params=(
                        self.params.dict(exclude_none=True, exclude_unset=True)
                        if self.params
                        else None
                    ),
                    headers=self.headers,
                    timeout=30,
                )
                print(f"[SCRAPER] Response status: {response.status_code}")
                if response.status_code != 200:
                    print(f"[SCRAPER] ❌ Error response: {response.text[:1000]}")
                return response
            except requests.exceptions.Timeout:
                print(f"[SCRAPER] ⏱️ Request timeout (attempt {retry_count + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError as e:
                print(f"[SCRAPER] 🔌 Connection error (attempt {retry_count + 1}/{self.max_retries}): {str(e)[:200]}")
            except ValueError as e:
                print(f"[SCRAPER] ❌ Value Error (attempt {retry_count + 1}/{self.max_retries}): {e}")
            except Exception as e:
                print(f"[SCRAPER] ❌ Exception (attempt {retry_count + 1}/{self.max_retries}): {str(e)[:200]}")
            finally:
                retry_count += 1
            if retry_count < self.max_retries:
                print(f"[SCRAPER] 🔄 Retrying request ({retry_count}/{self.max_retries})...")
        print(f"[SCRAPER] ❌ All {self.max_retries} retry attempts failed")
        return None
