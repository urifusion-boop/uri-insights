from typing import List
from app.domain.enums.socialmediapost_enum import PostTypeEnum
from app.domain.enums.twitter_enum import TwitterEnum
from app.domain.requests.twitter_requests import CreateTweetPayload


class TwitterHelper:
    @staticmethod
    def clean_payload_for_tweet_creation(payload: dict):
        return {key: value for key, value in payload.items() if value is not None}

    @staticmethod
    def clean_additional_owners_input_for_simple_media_upload(
        additional_owners: List[int | str],
    ):
        if additional_owners:
            return [item for item in additional_owners if item]

    @staticmethod
    def create_twitter_post_payload_from_post_dict(payload: dict) -> CreateTweetPayload:
        if payload["post_type"] == PostTypeEnum.TWEET:
            result_payload = CreateTweetPayload(
                text=payload["content"],
                media=None,  # PENDING UPDATE
                direct_message_deep_link=None,
                for_super_followers_only=None,
                geo=None,
                poll=None,
                quote_tweet_id=None,
                reply=None,
                reply_settings=None,
            )
            return result_payload
        return CreateTweetPayload()

    @staticmethod
    def prep_search_response_for_leads_gen(search_response: dict):
        search_response_data = search_response.get("data", [])
        search_response_authors = search_response.get("includes", {}).get("users", [])

        if not search_response_data:
            raise ValueError("No data gotten from twitter")

        if search_response_authors:
            # Build a lookup dictionary from authors by id
            author_lookup = {author["id"]: author for author in search_response_authors}

            # Attach author to each post
            for post in search_response_data:
                author_id = post.get("author_id")
                if author_id and author_id in author_lookup:
                    post["author"] = author_lookup[author_id]

        return search_response_data

    @staticmethod
    def trunc_twitter_query(
        query_parts_one: List[str], query_parts_two: List[str]
    ) -> str:
        query_parts_one_joined = " ".join(query_parts_one)
        query_parts_two_joined = " ".join(query_parts_two)
        query_len_one = len(query_parts_one_joined)
        query_len_two = len(query_parts_two_joined)

        if (query_len_one + query_len_two) >= TwitterEnum.QUERY_STRING_CHAR_LIMIT.value:
            diff = abs(query_len_one - query_len_two)
            query_parts_one_joined = query_parts_one_joined[:diff].rstrip()

        return query_parts_one_joined + " " + query_parts_two_joined
