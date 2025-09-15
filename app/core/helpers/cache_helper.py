import base64
import json
from typing import Dict, Any, Union


class CacheHelper:
    @staticmethod
    def generate_cache_key(identifier: Union[str, Dict[str, Any]]) -> str:
        """
        Generates a unique cache key based on the request identifier.
        Encodes the identifier as a base64 string for consistent, unique keys.

        Args:
            identifier (str or dict): The unique identifier for the request.
                                      This can be a URL, a JSON payload, or any unique string representation.

        Returns:
            str: A unique base64-encoded cache key.
        """
        # Convert dictionary identifiers to a JSON string
        if isinstance(identifier, dict):
            identifier = json.dumps(identifier, sort_keys=True)

        # Encode the identifier with base64
        return base64.urlsafe_b64encode(identifier.encode()).decode()
