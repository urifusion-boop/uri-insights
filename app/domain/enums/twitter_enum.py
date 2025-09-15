from enum import Enum


class TwitterEnum(Enum):
    TWEET_FIELDS = "attachments,author_id,context_annotations,conversation_id,created_at,edit_controls,edit_history_tweet_ids,entities,geo,id,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings,text,withheld"
    USER_FIELDS = "id,username,connection_status,created_at,description,entities,location,pinned_tweet_id,profile_image_url,public_metrics,url,verified,withheld"
    MEDIA_FIELDS = "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width,alt_text,variants"
    POLL_FIELDS = "id,options,duration_minutes,end_datetime,voting_status"
    PLACE_FIELDS = (
        "full_name,id,contained_within,country,country_code,geo,name,place_type"
    )
    EXPANSIONS = "author_id,entities.mentions.username,in_reply_to_user_id,geo.place_id"
    USER_TWEET_FIELDS = (
        "attachments,author_id,context_annotations,conversation_id,"
        "created_at,edit_controls,entities,geo,id,in_reply_to_user_id,"
        "lang,non_public_metrics,public_metrics,organic_metrics,"
        "promoted_metrics,possibly_sensitive,referenced_tweets,"
        "reply_settings,source,text,withheld"
    )
    AUTH_USER_FIELDS = (
        "created_at,description,entities,id,location,most_recent_tweet_id,"
        "name,pinned_tweet_id,profile_image_url,protected,public_metrics,"
        "url,username,verified,verified_type,withheld"
    )
    QUERY_STRING_CHAR_LIMIT = 512


class MediaCategory(Enum):
    TWEET_IMAGE = "tweet_image"
    TWEET_VIDEO = "tweet_video"
    TWEET_GIF = "tweet_gif"
    DM_IMAGE = "dm_image"
    DM_VIDEO = "dm_video"
    DM_GIF = "dm_gif"
    SUBTITLES = "subtitles"
