from app.domain.adapters.FacebookAdapter import FacebookAdapter
from app.domain.adapters.GoogleAdapter import GoogleAdapter
from app.domain.adapters.InstagramAdapter import InstagramAdapter
from app.domain.adapters.MentionAdapter import MentionAdapter
from app.domain.adapters.RedditAdapter import RedditAdapter
from app.domain.adapters.LinkedinAdapter import LinkedinAdapter


class AdapterFactory:
    @staticmethod
    def get_adapter(platform: str, data: dict):
        adapters = {
            "google": GoogleAdapter,
            "reddit": RedditAdapter,
            "mention": MentionAdapter,
            "facebook": FacebookAdapter,
            "instagram": InstagramAdapter,
            "linkedin": LinkedinAdapter,
        }
        if platform not in adapters.keys():
            raise ValueError(f"No adapter found for platform: {platform}")
        adapter_class = adapters.get(platform, GoogleAdapter)
        return adapter_class(data)
