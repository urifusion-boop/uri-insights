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
                )
                return response
            except ValueError as e:
                print("Value Error occurred in async data scraping: ", e)
            except Exception as e:
                print("Exception occurred: ", e)
            finally:
                retry_count += 1
            print("Retrying request")
