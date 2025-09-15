from typing import Any


class ObjectHelper:
    @staticmethod
    def transform_twitter_fields_params(params: Any) -> dict:
        # Convert params to dictionary, excluding None values
        params_dict = params.dict(exclude_none=True) if params else {}

        # Replace specific keys for API-compliant parameter names
        replacement_map = {
            "poll_fields": "poll.fields",
            "media_fields": "media.fields",
            "place_fields": "place.fields",
            "tweet_fields": "tweet.fields",
            "user_fields": "user.fields",
        }

        # Apply the replacements
        transformed_params = {
            replacement_map.get(key, key): value for key, value in params_dict.items()
        }
        return transformed_params
