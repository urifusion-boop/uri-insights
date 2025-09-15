import pycountry
import re


class LocationProcessor:
    @staticmethod
    def normalize_location(location: str) -> str:
        """
        Normalize location strings by:
        - Stripping spaces
        - Removing punctuation
        - Converting to title case
        - Removing special characters
        """
        if not location:
            return "Unknown"
        # Remove trailing punctuation and extra spaces
        location = location.strip().rstrip(".")
        # Remove special characters like emojis
        location = re.sub(r"[^\w\s,]", "", location)
        # Convert to title case for consistency
        return location.title()

    @staticmethod
    async def extract_country(location: str) -> str:
        """
        Extract country name from a location string if possible.
        Assign to 'World' if no valid country is identified.
        """
        normalized_location = LocationProcessor.normalize_location(location)

        # Step 1: Check for exact or partial country name matches
        country_matches = []
        for country in pycountry.countries:
            if (
                f", {country.name}" in normalized_location
                or country.name in normalized_location.split()
            ):
                country_matches.append(country.name)

        if country_matches:
            # Return the longest match (e.g., "Nigeria" over "Niger")
            return max(country_matches, key=len)

        # Step 2: Attempt fuzzy matching
        try:
            matches = pycountry.countries.search_fuzzy(normalized_location)
            if matches:
                return matches[0].name
        except LookupError:
            pass

        # Default to 'World'
        return "World"
