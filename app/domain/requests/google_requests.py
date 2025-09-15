from typing import List, Optional
from pydantic import BaseModel
from fastapi import Query


class GoogleSearchParams(BaseModel):
    """
    Represents query parameters for a Google Custom Search request, allowing
    for robust keyword tracking with fine-tuned customization.

    Attributes:
        includes: List of keywords to include in the search query.
        excludes: List of keywords to exclude from the search results.
        phrases: List of exact phrases to include in the search, each phrase enclosed in double quotes.
        locations: Domains or sites to restrict search results (e.g., 'site:example.com').
        languages: Languages to restrict search results (e.g., 'lang_en' for English).
        platforms: Specific sites or platforms to prioritize in the search query.
        start_index: The starting index for pagination, typically a multiple of count (e.g., 1, 11, 21).
        num: Number of results per page (between 1 and 10).
        lr: Restricts results to documents in a specified language (e.g., 'lang_en' for English).
        safe: Enables or disables safe search filtering ('active' or 'off').
        cx: The Custom Search Engine ID to use for the request.
        sort: The order of the search results (e.g., 'date' for most recent).
        filter: Duplicate content filtering (1 to enable, 0 to disable).
        gl: Geolocation country code to fine-tune results based on a location (e.g., 'US' for United States).
        cr: Restricts search results to a specific country (e.g., 'countryUS' for United States).
        googlehost: Specifies the Google domain to use (e.g., 'google.com' or 'google.co.uk').
        c2coff: Disables translation between Simplified and Traditional Chinese ('1' to disable).
        hq: Additional query terms to emphasize in the search.
        hl: Interface language for the Google search engine (e.g., 'en' for English).
        site_search: Restricts search results to a specific site (e.g., 'example.com').
        site_search_filter: Site search filtering ('i' includes, 'e' excludes site from results).
        exact_terms: Terms that must appear in search results exactly as provided.
        exclude_terms: Terms to exclude from search results.
        link_site: Restricts results to pages that link to a specific URL.
        or_terms: Alternative terms for an OR search, separated by spaces.
        date_restrict: Limits results to documents published within a specific date range (e.g., 'd7' for last 7 days).
        low_range: Specifies the lower bound for a numeric range search.
        high_range: Specifies the upper bound for a numeric range search.
        search_type: Specifies the type of search (e.g., 'image' for image search).
        file_type: Restricts results to a specific file type (e.g., 'pdf').
        rights: Filters results by usage rights (e.g., 'cc_publicdomain' for public domain content).
        img_size: Specifies the desired image size for image search (e.g., 'medium', 'large').
        img_type: Filters image search results by type (e.g., 'photo', 'clipart').
        img_color_type: Specifies the desired color type in image search (e.g., 'blackandwhite', 'color').
        img_dominant_color: Filters image search results by dominant color (e.g., 'red', 'blue').
    """

    includes: Optional[List[str]] = Query(
        None, description="Keywords to include in the search"
    )
    excludes: Optional[List[str]] = Query(
        None, description="Keywords to exclude from the search"
    )
    phrases: Optional[List[str]] = Query(None, description="Exact phrases to include")
    locations: Optional[List[str]] = Query(
        None, description="Locations for site-specific searches"
    )
    languages: Optional[List[str]] = Query(None, description="Language restrictions")
    platforms: Optional[List[str]] = Query(None, description="Platform restrictions")
    start: int = Query(1, description="Pagination start index")
    num: int = Query(10, description="Number of results per page")
    lr: Optional[str] = Query(None, description="Language restriction")
    safe: Optional[str] = Query(None, description="Safe search setting")
    sort: Optional[str] = Query("date", description="Sort order")
    filter: Optional[int] = Query(1, description="Duplicate content filter")
    gl: Optional[str] = Query(None, description="Geolocation country code")
    cr: Optional[str] = Query(None, description="Country restriction")
    googlehost: Optional[str] = Query(None, description="Google domain")
    c2coff: Optional[str] = Query(None, description="Chinese translation control")
    hq: Optional[str] = Query(None, description="Additional query emphasis")
    hl: Optional[str] = Query(None, description="Interface language")
    site_search: Optional[str] = Query(None, description="Site-specific search")
    site_search_filter: Optional[str] = Query(None, description="Site search filter")
    exact_terms: Optional[str] = Query(None, description="Exact terms to include")
    exclude_terms: Optional[str] = Query(None, description="Terms to exclude")
    link_site: Optional[str] = Query(
        None, description="Restrict to pages linking to URL"
    )
    or_terms: Optional[str] = Query(None, description="Alternative terms (OR search)")

    """
    # Using dateRestrict Parameter
    # The dateRestrict parameter accepts relative time periods, specified as:

    # d[number]: For days (e.g., d30 for the last 30 days)
    # w[number]: For weeks
    # m[number]: For months
    # y[number]: For years
    """
    date_restrict: Optional[str] = Query(
        "d30", description="Date restriction for results"
    )
    low_range: Optional[str] = Query(
        None, description="Low range for numeric range search"
    )
    high_range: Optional[str] = Query(
        None, description="High range for numeric range search"
    )
    search_type: Optional[str] = Query(None, description="Type of search (e.g., image)")
    file_type: Optional[str] = Query(None, description="Restrict by file type")
    rights: Optional[str] = Query(None, description="Filter by usage rights")
    img_size: Optional[str] = Query(None, description="Image size")
    img_type: Optional[str] = Query(None, description="Image type")
    img_color_type: Optional[str] = Query(None, description="Image color type")
    img_dominant_color: Optional[str] = Query(
        None, description="Dominant color for images"
    )
    max_search_iteration_count: int = 9

    class Config:
        use_enum_values = True

    """
    Represents query parameters for a Google Custom Search request, allowing
    for robust keyword tracking with fine-tuned customization.
    """
