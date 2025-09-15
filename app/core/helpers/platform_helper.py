class PlatformHelper:
    @staticmethod
    def get_platform(url: str) -> str:
        """
        Determines the platform based on the given URL.

        Args:
            url (str): The URL to check.

        Returns:
            str: The name of the platform if found, otherwise 'OTHERS'.
        """
        social_media_domains = {
            "tiktok.com": "TIKTOK",
            "instagram.com": "INSTAGRAM",
            "facebook.com": "FACEBOOK",
            "twitter.com": "X",
            "x.com": "X",
            "linkedin.com": "LINKEDIN",
            "threads.net": "THREADS",
            "reddit.com": "REDDIT",
            "snapchat.com": "SNAPCHAT",
            "pinterest.com": "PINTEREST",
        }
        for domain, platform in social_media_domains.items():
            if domain in url.lower():
                return platform
        return "OTHERS"
