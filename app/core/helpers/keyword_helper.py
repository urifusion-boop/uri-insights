from app.domain.factories.AdapterFactory import AdapterFactory


class KeywordHelper:
    @staticmethod
    def unify_tracker_data(web_data: dict):
        if web_data:
            unified_posts = []
            unified_influencers = []
            metadata = {
                "total_engagements": {
                    "like_count": 0,
                    "retweet_count": 0,
                    "quote_count": 0,
                    "reply_count": 0,
                }
            }
            total_engagements = metadata.get("total_engagements", {})
            for item in web_data.get("items", []):
                post_data = AdapterFactory.get_adapter("google", item).to_post()
                item_engagements = post_data.get("public_metrics")
                if item_engagements:
                    for key in total_engagements:
                        total_engagements[key] += item_engagements.get(key, 0)
                influencer = post_data.get("author", None)
                if influencer:
                    influencer_type = influencer.get("type", None)
                    if influencer_type:
                        influencer["type"] = influencer_type.value
                    unified_influencers.append(influencer)
                unified_posts.append(post_data)

            web_data.pop("items")
            web_data["metadata"] = metadata
            web_data["metadata"]["total_posts"] = len(unified_posts)

            web_data["posts"] = unified_posts
            web_data["influencers"] = unified_influencers

        return web_data
