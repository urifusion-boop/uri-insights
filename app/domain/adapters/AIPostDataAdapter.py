from datetime import datetime
from typing import List, Optional, Any
from app.domain.enums.aiposttype_enum import PostTypeEnum
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.requests.aipost_requests import AIPostStructure


class AIPostDataAdpater:
    @staticmethod
    async def adapt_posts(posts_data: List[dict], platform: PostPlatformEnum) -> Any:
        platform_adapters = {
            PostPlatformEnum.FACEBOOK: AIPostDataAdpater.__adapt_facebook_posts,
            PostPlatformEnum.INSTAGRAM: AIPostDataAdpater.__adapt_instagram_posts,
            PostPlatformEnum.LINKEDIN: AIPostDataAdpater.__adapt_linkedin_posts,
            # PostPlatformEnum.TIKTOK: AIPostDataAdpater.__adapt_tiktok_posts,
            # PostPlatformEnum.TWITTER: AIPostDataAdpater.__adapt_twitter_posts,
        }

        adapted_posts = await platform_adapters[platform](posts_data)
        return adapted_posts

    @staticmethod
    async def __adapt_facebook_posts(facebook_posts_data: List[dict]) -> List[dict]:
        adapted_posts = []

        for post in facebook_posts_data:
            media_type = None
            post_attachments = post.get("attachments", {}).get("data")
            if post_attachments and len(post_attachments) > 0:
                media_type = post_attachments[0].get("media_type")

            post_comments = post.get("comments", {}).get("data")
            post_reaction_count = (
                post.get("reactions", {}).get("summary", {}).get("total_count", 0)
            )
            created_time = post.get("created_time", "")
            post_time = datetime.strptime(
                created_time, "%Y-%m-%dT%H:%M:%S%z"
            ).isoformat()
            comment_count = len(post_comments) if post_comments else 0
            engagement_count = post_reaction_count + comment_count
            adapted_post = {
                "media_type": await AIPostDataAdpater.__map_media_type(media_type),
                "content": (
                    post_attachments[0].get("description", "")
                    if post_attachments
                    else ""
                ),
                "engagement_count": engagement_count,
                "comment_count": comment_count,
                "post_time": post_time,
            }

            adapted_posts.append(
                AIPostStructure(**adapted_post).dict(exclude_none=True)
            )
        return adapted_posts

    @staticmethod
    async def __adapt_instagram_posts(instagram_post_data: List[dict]) -> List[dict]:
        adapted_posts = []

        for post in instagram_post_data:
            comments_count = post.get("comments_count", 0)
            likes_count = post.get("like_count", 0)
            adapted_post = {
                "media_type": await AIPostDataAdpater.__map_media_type(
                    post.get("media_type", "text")
                ),
                "content": post.get("caption"),
                "engagement_count": likes_count + comments_count,
                "comment_count": comments_count,
                "post_time": post.get("timestamp"),
            }
            adapted_posts.append(
                AIPostStructure(**adapted_post).dict(exclude_none=True)
            )
        # TO DO: Implement instagram adapter for instagram business discovery.
        return adapted_posts

    @staticmethod
    async def __adapt_linkedin_posts(linkedin_post_data: List[dict]) -> List[dict]:
        adapted_posts = []

        for post in linkedin_post_data:
            post_specific_content = post.get("specificContent", {}).get(
                "com.linkedin.ugc.ShareContent", {}
            )
            post_text = post_specific_content.get("shareCommentary", {}).get("text", "")
            post_media_category = post_specific_content.get("shareMediaCategory", "")
            post_media_timestamp = post.get("created", {}).get("time", 0)
            comment_count = post.get("engagement_summary", {}).get("commentCount", 0)
            share_count = post.get("engagement_summary", {}).get("shareCount", 0)
            like_count = post.get("engagement_summary", {}).get("likeCount", 0)
            click_count = post.get("engagement_summary", {}).get("clickCount", 0)
            adapted_post = {
                "media_type": await AIPostDataAdpater.__map_media_type(
                    post_media_category
                ),
                "content": post_text,
                "engagement_count": sum(
                    [comment_count, share_count, like_count, click_count]
                ),
                "share_count": share_count,
                "comment_count": comment_count,
                "post_time": datetime.fromtimestamp(
                    post_media_timestamp / 1000
                ).isoformat(),
            }
            adapted_posts.append(
                AIPostStructure(**adapted_post).dict(exclude_none=True)
            )
        print(
            "\nAverage post length: ",
            await AIPostDataAdpater.__get_average_content_length(adapted_posts),
        )
        return adapted_posts

    # @staticmethod
    # def __adapt_tiktok_posts(tiktok_post_data: List[dict]) -> List[dict]:
    #     pass

    # @staticmethod
    # def __adapt_twitter_posts(twitter_post_data: List[dict]) -> List[dict]:
    #     pass

    @staticmethod
    async def __map_media_type(media_type: Optional[str]) -> Optional[PostTypeEnum]:
        if not media_type:
            return None
        media_type = media_type.lower()
        image_types = ["photo", "image", "picture"]
        video_types = ["video"]
        carousel_types = ["carousel", "album", "carousel_album"]
        article_types = ["article"]
        reel_types = ["reel"]

        if media_type in image_types:
            return PostTypeEnum.IMAGE
        elif media_type in video_types:
            return PostTypeEnum.VIDEO
        elif media_type in carousel_types:
            return PostTypeEnum.CAROUSEL
        elif media_type in article_types:
            return PostTypeEnum.ARTICLE
        elif media_type in reel_types:
            return PostTypeEnum.REEL
        else:
            return PostTypeEnum.TEXT  # Set text as ddefault post type

    @staticmethod
    async def __get_average_content_length(posts_data: List[dict]) -> float:
        result = 0
        length = len(posts_data)
        if length > 0:
            for post in posts_data:
                content_length = len(post.get("content", ""))
                result += content_length
            return result / length
        return 0
