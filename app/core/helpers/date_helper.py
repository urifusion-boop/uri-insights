from datetime import date, datetime, timedelta, timezone
import re
from typing import Optional, Union
from app.domain.enums.date_enum import DateFilterEnum
from app.core.config import settings


class DateHelper:
    @staticmethod
    def parse_date(date_str: str):
        """
        Convert a date string to a consistent date object format (YYYY-MM-DD).

        Args:
            date_str (str): Date string to be parsed.

        Returns:
            datetime.date or None: Parsed date object or None if parsing fails.
        """
        # Handle ISO 8601 (e.g., "2024-10-11T05:00:21+00:00")
        try:
            return datetime.fromisoformat(date_str).date()
        except ValueError:
            pass

        # Handle relative dates (e.g., "2 days ago")
        relative_match = re.match(
            r"(\d+)\s(hours?|days?|weeks?|months?|years?)\sago", date_str
        )
        if relative_match:
            value, unit = int(relative_match.group(1)), relative_match.group(2)
            today = datetime.now()
            if "day" in unit:
                return today - timedelta(days=value)
            elif "hour" in unit:
                return today - timedelta(hours=value)
            elif "week" in unit:
                return today - timedelta(weeks=value)
            elif "month" in unit:
                return today - timedelta(days=value * 30)
            elif "year" in unit:
                return today - timedelta(days=value * 365)

        # Handle common date formats with both potential orders
        for fmt in ["%d %b %Y", "%b %d, %Y"]:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        # Log unsupported date formats
        print(f"Unsupported date format: {date_str}")
        return None

    @staticmethod
    def generate_unix_timestamp_range(
        until: datetime, days_to_subtract: int = 28
    ) -> dict:
        """
        Generates a Unix timestamp range for a given `until` date and a relative past range.

        Args:
            until (datetime): The upper bound datetime.
            days_to_subtract (int): Number of days to subtract for the lower bound.

        Returns:
            dict: A dictionary containing 'since' and 'until' Unix timestamps.
        """
        now = datetime.now()
        since = now - timedelta(days=days_to_subtract)

        # Adjust `until` if it's in the past
        if until < since:
            until = now

        return {"since": int(since.timestamp()), "until": int(until.timestamp())}

    @staticmethod
    def format_to_iso8601(date_str: str) -> str:
        """
        Converts a date string into a standardized ISO 8601 format (`%Y-%m-%dT%H:%M:%S.%fZ`).
        Handles various input formats and edge cases.

        Args:
            date_str (str): The date string to be formatted.

        Returns:
            str: A formatted ISO 8601 string.
        """
        formats_to_try = [
            "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO 8601 with fractional seconds and timezone
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO 8601 with fractional seconds, no timezone
            "%Y-%m-%dT%H:%M:%S",  # ISO 8601 without fractional seconds or timezone
            "%Y-%m-%d %H:%M:%S",  # Common format with space separator
            "%Y-%m-%d",  # Date only
        ]

        for fmt in formats_to_try:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Convert to ISO 8601 with `Z` as UTC indicator
                if parsed_date.tzinfo:
                    return parsed_date.astimezone().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                return parsed_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                continue

        # If all formats fail, clean and reprocess
        cleaned_date_str = DateHelper.clean_date_string(date_str)
        try:
            parsed_date = datetime.fromisoformat(cleaned_date_str)
            return parsed_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            # Default to current time if parsing fails
            now = datetime.now()
            print(
                f"Unrecognized date format: '{date_str}'. Defaulting to current time."
            )
            return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def clean_date_string(date_str: str) -> str:
        """
        Cleans and normalizes a date string to help with parsing.

        Args:
            date_str (str): The raw date string.

        Returns:
            str: A cleaned date string.
        """
        # Remove unwanted characters (e.g., Z or timezone offsets)
        date_str = date_str.replace("Z", "").strip()
        date_str = re.sub(r"(\+\d{2}:\d{2})", "", date_str)  # Remove timezone offsets
        return date_str

    @staticmethod
    def combine_date_and_time(date_str: str, time_str: str) -> datetime:
        """
        Combines a date string and a time string into a datetime object.

        Args:
            date_str (str): The date string.
            time_str (str): The time string.

        Returns:
            datetime: Combined datetime object.
        """
        try:
            formatted_date = DateHelper.format_to_iso8601(date_str)
            formatted_time = DateHelper.format_to_iso8601(time_str)

            # Convert to datetime objects
            date_part = datetime.strptime(
                formatted_date, "%Y-%m-%dT%H:%M:%S.%fZ"
            ).date()
            time_part = datetime.strptime(
                formatted_time, "%Y-%m-%dT%H:%M:%S.%fZ"
            ).time()

            return datetime.combine(date_part, time_part)
        except Exception as e:
            print(f"Error combining date and time: {e}")
            return datetime.now()  # Default to current time if parsing fails

    @staticmethod
    def get_date_range(filter_option: DateFilterEnum):
        """Returns start and end dates based on predefined date filters."""
        end_date = datetime.utcnow().replace(
            microsecond=0, second=0, minute=0
        )  # Ensure consistency
        time_deltas = {
            DateFilterEnum.LAST_24_HOURS: timedelta(days=1),
            DateFilterEnum.LAST_3_DAYS: timedelta(days=3),
            DateFilterEnum.LAST_7_DAYS: timedelta(days=7),
            DateFilterEnum.LAST_1_WEEK: timedelta(weeks=1),
            DateFilterEnum.LAST_2_WEEKS: timedelta(weeks=2),
            DateFilterEnum.LAST_1_MONTH: timedelta(days=30),
            DateFilterEnum.LAST_2_MONTHS: timedelta(days=60),
            DateFilterEnum.LAST_3_MONTHS: timedelta(days=90),
        }

        start_date = end_date - time_deltas.get(
            filter_option, timedelta(days=7)
        )  # Default to 7 days if invalid
        return start_date, end_date

    @staticmethod
    def generate_next_lead_generation_date():
        """Returns the next generation date for a lead business info."""
        return datetime.utcnow() + timedelta(hours=settings.LEAD_GENERATION_INTERVAL)

    @staticmethod
    def to_iso_format(ms_timestamp: int):
        """
        Convert timestamp in milliseconds to iso string format
        """
        if ms_timestamp > 0:
            dt = datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%S+0000")

    @staticmethod
    def to_readable_human_format(
        datetime_data: Union[str, datetime, date]
    ) -> Optional[str]:
        """
        Accept datetime data in string format or datetime/date object and
        transform it to a readable human format (e.g., "Jul 28, 2025").
        Returns None if parsing fails.
        """
        if isinstance(datetime_data, (datetime, date)):
            raw_datetime = datetime_data
        elif isinstance(datetime_data, str):
            # Normalize 'Z' to '+00:00' if present
            iso_candidate = datetime_data.strip().replace("Z", "+00:00")

            try:
                raw_datetime = datetime.fromisoformat(iso_candidate)
            except ValueError:
                # fallback patterns
                for fmt in ["%d %b %Y", "%b %d, %Y"]:
                    try:
                        raw_datetime = datetime.strptime(datetime_data.strip(), fmt)
                        break
                    except ValueError:
                        raw_datetime = None
        else:
            return None

        if not raw_datetime:
            return None

        return raw_datetime.strftime("%d %b %y")  # e.g., "Jul 28, 2025"
