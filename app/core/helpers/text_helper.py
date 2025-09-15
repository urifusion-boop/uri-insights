from collections import Counter
from datetime import datetime, timezone
from app.core.helpers.dict_helper import DictHelper
from app.core.helpers.date_helper import DateHelper
import json
import re
from typing import Any, List, Optional


class TextHelper:
    @staticmethod
    def construct_query_url(data: Any) -> str:
        """
        Construct URL query string from data. Accepts both dict and objects with a .dict() method.
        """
        # Convert to dictionary if the object has a .dict() method
        if hasattr(data, "dict"):
            data = data.dict()

        # Construct query string with non-None values
        params = {k: v for k, v in data.items() if v is not None}
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return query_string

    @staticmethod
    def construct_query(data: dict[str, Any]) -> str:
        """
        Construct URL query string from a dictionary of parameters.
        """
        params = {}
        for k, v in data.items():
            if v is None:
                continue
            # If the value is a list, join it with commas
            if isinstance(v, list):
                params[k] = ",".join(map(str, v))
            else:
                params[k] = v

        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return query_string

    @staticmethod
    def to_string(data: Any) -> str:
        """
        Converts the instance's non-null values into a single concatenated string
        in JSON-like format, ensuring consistent serialization.

        Returns:
            str: A JSON-like string representation of the instance's fields and values.
        """
        # Extract only the fields that are not None
        data = {key: value for key, value in data.dict().items() if value is not None}
        # Convert to JSON string
        return json.dumps(data, sort_keys=True)

    @staticmethod
    def is_url(text: str) -> bool:
        return (
            text.startswith("http://")
            or text.startswith("https://")
            or text.startswith("@https://")
        )

    @staticmethod
    def is_valid_country_code(code: str):
        valid_country_codes = [
            "ad",
            "ae",
            "af",
            "ag",
            "ai",
            "al",
            "am",
            "ao",
            "ar",
            "as",
            "at",
            "au",
            "aw",
            "ax",
            "az",
            "ba",
            "bb",
            "bd",
            "be",
            "bf",
            "bg",
            "bh",
            "bi",
            "bj",
            "bl",
            "bm",
            "bn",
            "bo",
            "bq",
            "br",
            "bs",
            "bt",
            "bv",
            "bw",
            "by",
            "bz",
            "ca",
            "cc",
            "cd",
            "cf",
            "cg",
            "ch",
            "ci",
            "ck",
            "cl",
            "cm",
            "cn",
            "co",
            "cr",
            "cu",
            "cv",
            "cw",
            "cx",
            "cy",
            "cz",
            "de",
            "dj",
            "dk",
            "dm",
            "do",
            "dz",
            "ec",
            "ee",
            "eg",
            "eh",
            "er",
            "es",
            "et",
            "fi",
            "fj",
            "fk",
            "fm",
            "fo",
            "fr",
            "ga",
            "gb",
            "gd",
            "ge",
            "gf",
            "gg",
            "gh",
            "gi",
            "gl",
            "gm",
            "gn",
            "gp",
            "gq",
            "gr",
            "gs",
            "gt",
            "gu",
            "gw",
            "gy",
            "hk",
            "hm",
            "hn",
            "hr",
            "ht",
            "hu",
            "id",
            "ie",
            "il",
            "im",
            "in",
            "io",
            "iq",
            "ir",
            "is",
            "it",
            "je",
            "jm",
            "jo",
            "jp",
            "ke",
            "kg",
            "kh",
            "ki",
            "km",
            "kn",
            "kp",
            "kr",
            "kw",
            "ky",
            "kz",
            "la",
            "lb",
            "lc",
            "li",
            "lk",
            "lr",
            "ls",
            "lt",
            "lu",
            "lv",
            "ly",
            "ma",
            "mc",
            "md",
            "me",
            "mf",
            "mg",
            "mh",
            "mk",
            "ml",
            "mm",
            "mn",
            "mo",
            "mp",
            "mq",
            "mr",
            "ms",
            "mt",
            "mu",
            "mv",
            "mw",
            "mx",
            "my",
            "mz",
            "na",
            "nc",
            "ne",
            "nf",
            "ng",
            "ni",
            "nl",
            "no",
            "np",
            "nr",
            "nu",
            "nz",
            "om",
            "pa",
            "pe",
            "pf",
            "pg",
            "ph",
            "pk",
            "pl",
            "pm",
            "pn",
            "pr",
            "pt",
            "pw",
            "py",
            "qa",
            "re",
            "ro",
            "rs",
            "ru",
            "rw",
            "sa",
            "sb",
            "sc",
            "sd",
            "se",
            "sg",
            "sh",
            "si",
            "sj",
            "sk",
            "sl",
            "sm",
            "sn",
            "so",
            "sr",
            "ss",
            "st",
            "sv",
            "sx",
            "sy",
            "sz",
            "tc",
            "td",
            "tf",
            "tg",
            "th",
            "tj",
            "tk",
            "tl",
            "tm",
            "tn",
            "to",
            "tr",
            "tt",
            "tv",
            "tw",
            "tz",
            "ua",
            "ug",
            "um",
            "us",
            "uy",
            "uz",
            "va",
            "vc",
            "ve",
            "vg",
            "vi",
            "vn",
            "vu",
            "wf",
            "ws",
            "ye",
            "yt",
            "za",
            "zm",
            "zw",
        ]

        return code in valid_country_codes

    @staticmethod
    def extract_timestamp_from_text(text: Optional[str]) -> Optional[str]:
        # Extract timestamp from text using regex
        if not text:
            return None
        timestamp_pattern = r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\b"
        timestamp_match = re.search(timestamp_pattern, text)
        if timestamp_match:
            return timestamp_match.group(0)
        return None

    @staticmethod
    def extract_timestamp_from_date_text(text: Optional[str]) -> Optional[str]:
        # Extract date from text using regex
        if not text:
            return None
        # Regex for extracting date formats
        date_match = re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4}", text
        )
        if date_match:
            dt = datetime.strptime(date_match.group(), "%b %d, %Y").replace(
                tzinfo=timezone.utc
            )
            return dt.isoformat()
        return None

    @staticmethod
    def extract_timestamp_from_relative_date_text(text: Optional[str]) -> Optional[str]:
        # Extract date from text using regex
        if not text:
            return None
        date_match = re.search(
            r"(\d+)\s(hours?|days?|weeks?|months?|years?)\sago", text
        )
        if date_match:
            datetime_data = DateHelper.parse_date(date_match.group())
            if datetime_data:
                date_time = datetime_data.replace(tzinfo=timezone.utc)
                return date_time.isoformat()
        return None

    @staticmethod
    def generate_export_name(form_title, report_type):
        now = datetime.now()
        export_name = now.strftime("%A, %B %d, %Y %I:%M %p")
        return f"{form_title} {report_type} {export_name}"

    @staticmethod
    def extract_hashtags(text: str, hashtag: Optional[str] = None) -> List[str]:
        """
        Extracts hashtags from text. If `hashtag` is given, only that tag
        is returned (including the ‘#’); otherwise returns all tags.
        """
        if hashtag:
            tokens = text.split()
            mentions = [t for t in tokens if t == hashtag]
            return mentions
        else:
            # fallback: grab any '#' followed by word characters
            pattern = r"#\w+"

        return re.findall(pattern, text)

    @staticmethod
    def compute_hashtag_frequency(
        posts: List[dict], text_key: str, max_hashtags: int = 20
    ) -> List[dict]:
        hashtags = []
        for post in posts:
            post_hashtags = TextHelper.extract_hashtags(post.get(text_key, ""))
            if not post_hashtags:
                continue
            hashtags.extend(post_hashtags)
        if not hashtags:
            print("No hashtags found in provided posts")
            return [{}]
        hashtag_counter = DictHelper.sort_dict_by_values(dict(Counter(hashtags)), True)
        result = [
            {"hashtag": key, "count": value}
            for i, (key, value) in enumerate(hashtag_counter.items())
            if i < max_hashtags
        ]
        return result

    @staticmethod
    def has_multiple_words(s: str) -> bool:
        return len(s.strip().split()) > 1
