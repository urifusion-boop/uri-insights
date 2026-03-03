"""
Google Maps Business Discovery Service

Uses both Google Places API Text Search and Nearby Search for flexible business discovery.

Text Search: Natural language queries like "small businesses in Ogba"
Nearby Search: Precise location-based searches with radius filtering

PRD Reference: Lead Generation Expansion - Google Maps Engine
"""

import httpx
from typing import List, Dict, Optional, Any
from app.core.config import settings


class GoogleMapsService:
    """Service for Google Maps/Places API integration"""

    BASE_URL_NEW = "https://places.googleapis.com/v1"
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    @staticmethod
    async def search_businesses(
        # Text search params
        query: Optional[str] = None,
        location: Optional[str] = None,

        # Nearby search params
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,

        # Common params
        business_types: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        exclude_closed: bool = True,
        max_results: int = 20,
        search_mode: str = "auto"
    ) -> List[Dict[str, Any]]:
        """
        Intelligent business search that picks the right API based on inputs

        Args:
            query: Natural language search query (e.g., "restaurants")
            location: Location name (e.g., "Ogba, Lagos")
            latitude: Latitude for precise search
            longitude: Longitude for precise search
            radius_km: Search radius in kilometers
            business_types: List of business types to filter
            min_rating: Minimum Google rating (0-5)
            exclude_closed: Exclude closed businesses
            max_results: Maximum results to return
            search_mode: "text", "nearby", or "auto"

        Returns:
            List of business data dictionaries
        """

        print(f"🗺️ [GoogleMapsService] Starting search - mode: {search_mode}")
        print(f"   Query: {query}, Location: {location}")
        print(f"   Coords: ({latitude}, {longitude}), Radius: {radius_km}km")

        # Auto mode: intelligently pick the right API
        if search_mode == "auto":
            # If query or location is provided, use Text Search (supports natural language)
            if query or location:
                search_mode = "text"
                print("🔍 AUTO: Detected query/location → Using Text Search API")
            # If only coordinates provided, use Nearby Search
            elif latitude and longitude and radius_km:
                search_mode = "nearby"
                print("🔍 AUTO: Detected coordinates → Using Nearby Search API")
            else:
                raise ValueError("Auto mode requires either (query/location) OR (lat/lng + radius)")

        # Execute the appropriate search method
        if search_mode == "text":
            print("🔍 Using Text Search API (natural language)")
            return await GoogleMapsService._text_search(
                query=query,
                location=location,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                business_types=business_types,
                min_rating=min_rating,
                exclude_closed=exclude_closed,
                max_results=max_results
            )
        elif search_mode == "nearby":
            if not (latitude and longitude and radius_km):
                raise ValueError("Nearby mode requires latitude, longitude, and radius_km")
            print("🔍 Using Nearby Search API (coordinate-based)")
            # Convert km to meters for the API
            radius_meters = radius_km * 1000
            return await GoogleMapsService._nearby_search(
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
                business_types=business_types,
                min_rating=min_rating,
                exclude_closed=exclude_closed,
                max_results=max_results
            )
        else:
            raise ValueError(f"Invalid search_mode: {search_mode}. Use 'auto', 'text', or 'nearby'")


    @staticmethod
    async def _text_search(
        query: str,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        business_types: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        exclude_closed: bool = True,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Text Search API - Natural language queries

        Best for: "small businesses in Ogba", "restaurants in Lagos"
        Supports both location string and lat/lng coordinates for location biasing
        """

        # Build search query
        search_query = query or "businesses"
        if location:
            search_query = f"{search_query} in {location}"

        print(f"   Final search query: '{search_query}'")

        url = f"{GoogleMapsService.BASE_URL_NEW}/places:searchText"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.internationalPhoneNumber,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.businessStatus,places.types,places.priceLevel"
        }

        body = {
            "textQuery": search_query,
            "languageCode": "en",
            "maxResultCount": max_results
        }

        # Add location bias - prefer coordinates if available, otherwise geocode location string
        if latitude and longitude:
            radius_meters = (radius_km * 1000) if radius_km else 5000.0
            body["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius_meters
                }
            }
            print(f"   Added location bias: ({latitude}, {longitude}) with {radius_meters}m radius")
        elif location:
            try:
                coords = await GoogleMapsService._geocode(location)
                body["locationBias"] = {
                    "circle": {
                        "center": coords,
                        "radius": 5000.0  # Default 5km bias
                    }
                }
                print(f"   Added location bias: {coords}")
            except Exception as e:
                print(f"⚠️ Could not geocode location '{location}': {e}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                response.raise_for_status()

            data = response.json()

            # Debug: Log first place structure
            if data.get("places") and len(data["places"]) > 0:
                print(f"   📋 Sample place data: {data['places'][0]}")

            results = GoogleMapsService._parse_places_response(
                data,
                min_rating=min_rating,
                exclude_closed=exclude_closed
            )

            print(f"✅ Text Search returned {len(results)} businesses")
            if results:
                print(f"   📋 Sample parsed lead: {results[0]}")
            return results

        except Exception as e:
            print(f"❌ Text Search failed: {e}")
            raise


    @staticmethod
    async def _nearby_search(
        latitude: float,
        longitude: float,
        radius_meters: float,
        business_types: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        exclude_closed: bool = True,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Nearby Search API - Precise location-based search

        Best for: "All restaurants within 2km of (6.6, 3.3)"
        """

        print(f"   Searching within {radius_meters}m of ({latitude}, {longitude})")

        url = f"{GoogleMapsService.BASE_URL_NEW}/places:searchNearby"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.internationalPhoneNumber,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.businessStatus,places.types,places.priceLevel"
        }

        body = {
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "radius": radius_meters
                }
            },
            "maxResultCount": max_results
        }

        if business_types:
            body["includedTypes"] = business_types
            print(f"   Filtering by types: {business_types}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                # Log response for debugging
                if response.status_code != 200:
                    print(f"❌ API Error {response.status_code}: {response.text}")

                response.raise_for_status()

            data = response.json()
            results = GoogleMapsService._parse_places_response(
                data,
                min_rating=min_rating,
                exclude_closed=exclude_closed
            )

            print(f"✅ Nearby Search returned {len(results)} businesses")
            return results

        except Exception as e:
            print(f"❌ Nearby Search failed: {e}")
            raise


    @staticmethod
    def _convert_price_level(price_level_str: Optional[str]) -> Optional[int]:
        """
        Convert Google's NEW API price level string to integer

        NEW API: "PRICE_LEVEL_FREE", "PRICE_LEVEL_INEXPENSIVE", etc.
        Database: 0 (unspecified), 1 (free), 2-5 (inexpensive to very expensive)

        Source: https://developers.google.com/maps/documentation/places/web-service/reference/rpc/google.maps.places.v1#pricelevel
        """
        if not price_level_str:
            return None

        price_level_map = {
            "PRICE_LEVEL_UNSPECIFIED": 0,
            "PRICE_LEVEL_FREE": 1,
            "PRICE_LEVEL_INEXPENSIVE": 2,
            "PRICE_LEVEL_MODERATE": 3,
            "PRICE_LEVEL_EXPENSIVE": 4,
            "PRICE_LEVEL_VERY_EXPENSIVE": 5,
        }

        return price_level_map.get(price_level_str)

    @staticmethod
    def _parse_places_response(
        data: Dict,
        min_rating: Optional[float] = None,
        exclude_closed: bool = True
    ) -> List[Dict]:
        """Parse Google Places API response into URI lead format"""

        places = data.get("places", [])
        parsed_leads = []

        for place in places:
            # Apply filters
            rating = place.get("rating")
            business_status = place.get("businessStatus")

            # Skip if below minimum rating
            if min_rating and rating and rating < min_rating:
                continue

            # Skip if closed (and exclusion enabled)
            if exclude_closed and business_status in ["CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"]:
                continue

            # Extract data
            lead = {
                "google_place_id": place.get("id"),
                "company_name": place.get("displayName", {}).get("text"),
                "formatted_address": place.get("formattedAddress"),
                "location": place.get("formattedAddress"),  # Alias for compatibility
                "latitude": place.get("location", {}).get("latitude"),
                "longitude": place.get("location", {}).get("longitude"),
                "phone": place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber"),
                "website_url": place.get("websiteUri"),
                "google_rating": rating,
                "google_reviews_count": place.get("userRatingCount"),
                "business_status": business_status,
                "business_types": place.get("types", []),
                "business_category": place.get("types", [None])[0] if place.get("types") else None,
                "price_level": GoogleMapsService._convert_price_level(place.get("priceLevel")),
                "lead_source": "Google Maps"
            }

            parsed_leads.append(lead)

        return parsed_leads


    @staticmethod
    async def _geocode(location: str) -> Dict[str, float]:
        """
        Convert address/location name to lat/lng using Geocoding API

        Args:
            location: Address or place name (e.g., "Ogba, Lagos")

        Returns:
            Dict with latitude and longitude
        """

        params = {
            "address": location,
            "key": settings.GOOGLE_PLACES_API_KEY
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(GoogleMapsService.GEOCODING_URL, params=params)
                response.raise_for_status()

            data = response.json()

            if data.get("results") and len(data["results"]) > 0:
                location_data = data["results"][0]["geometry"]["location"]
                return {
                    "latitude": location_data["lat"],
                    "longitude": location_data["lng"]
                }
            else:
                raise ValueError(f"No geocoding results for: {location}")

        except Exception as e:
            raise ValueError(f"Geocoding failed for '{location}': {str(e)}")
