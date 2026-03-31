"""
Google Maps Lead Form Auto-Population Examples

This file teaches the AI how to interpret ambiguous queries and expand them
with proper context for accurate Google Maps/Places API searches.

Key Patterns:
1. Detect ambiguous terms (acronyms, abbreviations, generic terms)
2. Use location + industry context to disambiguate
3. Expand search queries with synonyms and related terms
4. Exclude irrelevant business types
5. Set appropriate filters (radius, rating, business types)
"""

GOOGLE_MAPS_AUTOPOPULATE_EXAMPLES = """
### Example 1: Financial Services - POS Agents (Ambiguous Acronym)
User Input: "Find POS Offices in Akure"

Context Analysis:
- "POS" is ambiguous: could mean "Point of Sale" OR "Post Office"
- Location "Akure, Nigeria" → Financial services context → POS = Point of Sale
- "Offices" suggests business locations, not postal services

Output:
{
    "form_title": "POS Agents - Akure",
    "maps_search_mode": "text",
    "maps_search_query": "Point of Sale agents, mobile money agents, POS terminals, POS services",
    "maps_location": "Akure, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["finance", "point_of_interest"],
    "maps_min_rating": 3.0,
    "maps_exclude_closed": true,
    "maps_max_results": 30,
    "business_context": "Financial services - mobile payment and POS terminal providers",
    "excluded_terms": ["post office", "postal service", "mail", "courier"]
}

---

### Example 2: Food & Beverage - Restaurant Search
User Input: "I need restaurants in Lekki"

Context Analysis:
- Generic "restaurants" → Expand to include related food establishments
- Include various dining types: fine dining, fast food, cafes, eateries

Output:
{
    "form_title": "Restaurants - Lekki",
    "maps_search_mode": "text",
    "maps_search_query": "restaurants, dining, eateries, food establishments",
    "maps_location": "Lekki, Lagos, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["restaurant", "cafe", "meal_takeaway", "food"],
    "maps_min_rating": 3.5,
    "maps_exclude_closed": true,
    "maps_max_results": 40,
    "business_context": "Food and beverage - dining establishments",
    "excluded_terms": ["grocery store", "supermarket"]
}

---

### Example 3: Healthcare - Medical Facilities
User Input: "Find clinics and pharmacies near Victoria Island with good reviews"

Context Analysis:
- Healthcare services
- User wants quality ("good reviews") → Set min_rating to 4.0
- "near" suggests moderate radius

Output:
{
    "form_title": "Clinics & Pharmacies - Victoria Island",
    "maps_search_mode": "text",
    "maps_search_query": "medical clinics, pharmacies, healthcare centers, diagnostic centers",
    "maps_location": "Victoria Island, Lagos, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["hospital", "pharmacy", "doctor", "health"],
    "maps_min_rating": 4.0,
    "maps_exclude_closed": true,
    "maps_max_results": 25,
    "business_context": "Healthcare services - medical facilities and pharmacies",
    "excluded_terms": []
}

---

### Example 4: Fitness - Gym Search
User Input: "gyms in Abuja"

Context Analysis:
- Fitness industry
- "gyms" → Include fitness centers, workout spaces, yoga studios

Output:
{
    "form_title": "Gyms - Abuja",
    "maps_search_mode": "text",
    "maps_search_query": "gyms, fitness centers, workout facilities, fitness studios",
    "maps_location": "Abuja, Nigeria",
    "maps_radius_km": 10,
    "maps_business_types": ["gym", "spa"],
    "maps_min_rating": 3.5,
    "maps_exclude_closed": true,
    "maps_max_results": 30,
    "business_context": "Fitness and wellness - gym and workout facilities",
    "excluded_terms": []
}

---

### Example 5: Retail - Supermarkets
User Input: "supermarkets and grocery stores within 3km of Ikeja"

Context Analysis:
- Retail/shopping
- Specific radius mentioned: 3km
- Include various retail types

Output:
{
    "form_title": "Supermarkets - Ikeja (3km)",
    "maps_search_mode": "text",
    "maps_search_query": "supermarkets, grocery stores, convenience stores, mini marts",
    "maps_location": "Ikeja, Lagos, Nigeria",
    "maps_radius_km": 3,
    "maps_business_types": ["supermarket", "grocery_or_supermarket", "store"],
    "maps_min_rating": 3.0,
    "maps_exclude_closed": true,
    "maps_max_results": 25,
    "business_context": "Retail - grocery and food shopping",
    "excluded_terms": []
}

---

### Example 6: Personal Care - Beauty Services
User Input: "salons and spas in Port Harcourt"

Context Analysis:
- Personal care/beauty industry
- Include barbershops, nail salons, massage

Output:
{
    "form_title": "Salons & Spas - Port Harcourt",
    "maps_search_mode": "text",
    "maps_search_query": "beauty salons, hair salons, spas, barbershops, nail salons",
    "maps_location": "Port Harcourt, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["beauty_salon", "hair_care", "spa"],
    "maps_min_rating": 3.5,
    "maps_exclude_closed": true,
    "maps_max_results": 30,
    "business_context": "Personal care - beauty and grooming services",
    "excluded_terms": []
}

---

### Example 7: Automotive - Car Services
User Input: "Find mechanic shops and auto repair in Surulere"

Context Analysis:
- Automotive services
- Include various car service types

Output:
{
    "form_title": "Auto Repair - Surulere",
    "maps_search_mode": "text",
    "maps_search_query": "mechanic shops, auto repair, car repair, garage, car service",
    "maps_location": "Surulere, Lagos, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["car_repair"],
    "maps_min_rating": 3.0,
    "maps_exclude_closed": true,
    "maps_max_results": 25,
    "business_context": "Automotive - vehicle repair and maintenance",
    "excluded_terms": []
}

---

### Example 8: Professional Services - Legal/Accounting
User Input: "law firms and accounting firms in Ikoyi"

Context Analysis:
- Professional services
- B2B focus

Output:
{
    "form_title": "Professional Services - Ikoyi",
    "maps_search_mode": "text",
    "maps_search_query": "law firms, legal services, accounting firms, audit firms",
    "maps_location": "Ikoyi, Lagos, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["lawyer", "accounting"],
    "maps_min_rating": 3.5,
    "maps_exclude_closed": true,
    "maps_max_results": 20,
    "business_context": "Professional services - legal and financial consulting",
    "excluded_terms": []
}

---

### Example 9: Hospitality - Hotels
User Input: "hotels and guest houses in Calabar with ratings above 4 stars"

Context Analysis:
- Hospitality/accommodation
- High quality requirement → min_rating 4.0+

Output:
{
    "form_title": "Hotels - Calabar (4+ stars)",
    "maps_search_mode": "text",
    "maps_search_query": "hotels, guest houses, lodges, accommodation",
    "maps_location": "Calabar, Nigeria",
    "maps_radius_km": 10,
    "maps_business_types": ["lodging", "hotel"],
    "maps_min_rating": 4.0,
    "maps_exclude_closed": true,
    "maps_max_results": 20,
    "business_context": "Hospitality - quality accommodation services",
    "excluded_terms": []
}

---

### Example 10: Education - Schools & Training
User Input: "training institutes and computer schools in Yaba"

Context Analysis:
- Education/training sector
- Tech training focus

Output:
{
    "form_title": "Training Institutes - Yaba",
    "maps_search_mode": "text",
    "maps_search_query": "training institutes, computer schools, tech academies, learning centers",
    "maps_location": "Yaba, Lagos, Nigeria",
    "maps_radius_km": 5,
    "maps_business_types": ["school"],
    "maps_min_rating": 3.0,
    "maps_exclude_closed": true,
    "maps_max_results": 25,
    "business_context": "Education - professional and technical training",
    "excluded_terms": []
}

---

### Pattern Summary for AI:

1. **Ambiguity Detection**:
   - Acronyms (POS, ATM, PC, AI, HR, etc.)
   - Generic terms (office, shop, store, center)
   - Multi-meaning words (bank = financial institution OR riverbank)

2. **Context Expansion**:
   - Use location to determine likely meaning
   - Add industry-specific synonyms
   - Include related business types
   - Consider local terminology (Nigeria: "chemist" = pharmacy)

3. **Query Enhancement Rules**:
   - Single word → Expand to phrase: "gym" → "gyms, fitness centers, workout facilities"
   - Acronym → Full form + variations: "POS" → "Point of Sale agents, mobile money agents, POS terminals"
   - Generic → Specific: "shops" → "retail stores, boutiques, shopping outlets"

4. **Exclusion Logic**:
   - Add "excluded_terms" for ambiguous queries
   - Example: Searching "POS" → exclude "post office, postal, mail"
   - Example: Searching "bank" for ATMs → exclude "river bank, blood bank"

5. **Business Type Mapping** (Google Places types):
   - Financial: finance, atm, bank
   - Food: restaurant, cafe, meal_takeaway, food
   - Health: hospital, pharmacy, doctor, dentist
   - Retail: store, supermarket, shopping_mall
   - Services: beauty_salon, gym, spa, car_repair
   - Professional: lawyer, accounting, real_estate_agency

6. **Quality Indicators**:
   - "good", "best", "top-rated" → min_rating: 4.0+
   - "any", "all" → min_rating: 3.0
   - "cheap", "affordable" → min_rating: 3.0, focus on results
   - No mention → min_rating: 3.0 (default)

7. **Radius Guidelines**:
   - "nearby", "near" → 5km
   - "within [X]km" → Use specified value
   - No mention → 5km (default)
   - Large city → 10km
   - Small town → 3km
"""
