"""
Lead Form Auto-Population Examples

This file contains diverse examples to train the AI on how to properly extract
lead form parameters for ANY use case. The AI should learn the PATTERN, not copy
these examples verbatim.

Key Pattern to Learn:
- category_context: FULL user description (not shortened)
- keywords: Direct explicit signals matching user's goal
- implied_keywords: Indirect problems/situations/frustrations
- competitors: Relevant alternatives in the space
- buying_signals: Phrases showing readiness/interest
- excluded_keywords: Language used by people on the OPPOSITE SIDE
"""

AUTOPOPULATE_EXAMPLES = """
### Example 1: SELLING Services (Fitness Coaching)
User Input: "I run a fitness coaching business in Lagos, Nigeria. I'm looking for people who need personal trainers, want to get fit, or are looking for workout guidance. My ideal customers are fitness enthusiasts, beginners, and people who recently moved to Lagos and need a trainer."

Output:
{{
    "form_title": "Fitness Coaching Leads - Lagos",
    "category_context": "I run a fitness coaching business in Lagos, Nigeria. I'm looking for people who need personal trainers, want to get fit, or are looking for workout guidance. My ideal customers are fitness enthusiasts, beginners, and people who recently moved to Lagos and need a trainer.",
    "intent_type": "sales",
    "keywords": ["personal trainer", "fitness coach", "need trainer", "looking for gym", "workout help", "fitness guidance"],
    "implied_keywords": ["can't lose weight", "out of shape", "getting fat", "new year resolution", "just moved to Lagos", "need accountability", "motivation lacking"],
    "competitors": ["F45", "Planet Fitness", "CrossFit Lagos", "Fit Fam", "Body by Design"],
    "ai_response_guide": "Respond as a friendly fitness coach offering free fitness assessment and personalized workout plans",
    "buying_signals": ["looking for trainer", "need workout plan", "want to get fit", "ready to start", "where can I find"],
    "excluded_keywords": ["I'm a personal trainer", "I offer training", "hire me as coach", "fitness coach available", "DM for rates", "book my sessions", "certified trainer here"],
    "location": ["Lagos", "Nigeria"],
    "post_age_filter": "all"
}}

---

### Example 2: HIRING Employees (Tech Recruiting)
User Input: "I'm a recruiter for a tech startup in Abuja. We're desperately hiring senior React developers and full-stack engineers. Looking for people from the past week who are actively job hunting, frustrated with their current roles, just got laid off, or complaining about low pay. Our ideal candidates have 3+ years experience and are open to relocation."

Output:
{{
    "form_title": "React Developers - Abuja Hiring",
    "category_context": "I'm a recruiter for a tech startup in Abuja. We're desperately hiring senior React developers and full-stack engineers. Looking for people from the past week who are actively job hunting, frustrated with their current roles, just got laid off, or complaining about low pay. Our ideal candidates have 3+ years experience and are open to relocation.",
    "intent_type": "hiring",
    "keywords": ["react developer", "full-stack engineer", "looking for job", "job hunting", "open to opportunities", "need a job"],
    "implied_keywords": ["laid off", "just got fired", "underpaid", "burnout", "toxic workplace", "job search", "career change", "frustrated at work", "between jobs", "unemployed"],
    "competitors": ["Google", "Meta", "Amazon", "Microsoft", "Interswitch", "Paystack", "Flutterwave"],
    "ai_response_guide": "Respond as a tech recruiter offering competitive salary, remote work options, and career growth opportunities",
    "buying_signals": ["actively looking", "open to relocation", "seeking new role", "available immediately", "ready for change"],
    "excluded_keywords": ["we're hiring", "looking for a developer", "seeking senior react", "join our team", "message me with your resume", "send me your portfolio", "apply now", "hiring for", "recruiting senior", "position available"],
    "location": ["Abuja", "Nigeria"],
    "post_age_filter": "7d"
}}

---

### Example 3: SELLING Products (Solar Panels)
User Input: "I sell solar panels and inverters across Nigeria. Looking for recent posts from people complaining about NEPA/power outages, high electricity bills, or businesses that need backup power in the last 30 days. Ideal customers are homeowners and small businesses tired of buying fuel for generators."

Output:
{{
    "form_title": "Solar Panel Customers - Nigeria",
    "category_context": "I sell solar panels and inverters across Nigeria. Looking for recent posts from people complaining about NEPA/power outages, high electricity bills, or businesses that need backup power in the last 30 days. Ideal customers are homeowners and small businesses tired of buying fuel for generators.",
    "intent_type": "sales",
    "keywords": ["need solar panels", "inverter needed", "backup power", "alternative power source", "looking for solar", "where to buy inverter"],
    "implied_keywords": ["NEPA is terrible", "no light again", "power outage", "high electricity bill", "generator fuel expensive", "tired of buying diesel", "business needs power", "constant outages"],
    "competitors": ["Arnergy", "Solar Sister", "Azuri Technologies", "Lumos", "SunFi"],
    "ai_response_guide": "Respond as a solar energy consultant offering free home assessment and flexible payment plans",
    "buying_signals": ["ready to buy", "need solar installation", "how much for inverter", "looking for reliable solar", "budget approved"],
    "excluded_keywords": ["I sell solar panels", "solar installation services", "we offer inverters", "contact us for solar", "best solar deals", "DM for quote", "solar business", "inverter supplier"],
    "location": ["Nigeria"],
    "post_age_filter": "30d"
}}

---

### Example 4: BUYING Services (Need a Plumber)
User Input: "Need a plumber in Lagos ASAP"

Output:
{{
    "form_title": "Plumber Search - Lagos",
    "category_context": "Need a plumber in Lagos ASAP",
    "intent_type": "other",
    "keywords": ["plumber available", "plumbing services", "I'm a plumber", "plumber in Lagos"],
    "implied_keywords": ["pipe burst", "leak repair", "toilet blocked", "water heater broken", "emergency plumbing"],
    "competitors": [],
    "ai_response_guide": "Respond as someone seeking urgent plumbing help for a pipe burst or leak",
    "buying_signals": ["available now", "can come today", "emergency service", "24/7 plumber"],
    "excluded_keywords": ["looking for plumber", "need plumber urgently", "plumbing emergency", "where to find plumber", "ISO plumber"],
    "location": ["Lagos"]
}}

---

### Example 5: SELLING Services (Freelance Copywriter)
User Input: "I'm a freelance copywriter looking for clients. I want to find business owners who struggle with writing content or need help with their websites."

Output:
{{
    "form_title": "Copywriting Clients",
    "category_context": "I'm a freelance copywriter looking for clients. I want to find business owners who struggle with writing content or need help with their websites.",
    "intent_type": "sales",
    "keywords": ["need copywriter", "looking for writer", "content writer needed", "help with website copy", "need blog posts"],
    "implied_keywords": ["can't write", "bad at writing", "website needs content", "no time to write", "struggling with copy", "my content sucks", "writer's block"],
    "competitors": ["Fiverr writers", "Upwork", "Toptal", "Contently"],
    "ai_response_guide": "Respond as a professional copywriter offering free content audit and website copy consultation",
    "buying_signals": ["hiring copywriter", "need content asap", "budget for writer", "looking to hire", "website launch soon"],
    "excluded_keywords": ["I'm a copywriter", "copywriting services", "hire me for content", "freelance writer available", "check out my portfolio", "DM for writing", "content creator here"],
    "location": []
}}

---

### Example 6: HIRING Staff (Virtual Assistant)
User Input: "Want to hire a virtual assistant"

Output:
{{
    "form_title": "Virtual Assistant Search",
    "category_context": "Want to hire a virtual assistant",
    "intent_type": "hiring",
    "keywords": ["virtual assistant", "VA available", "looking for VA work", "remote assistant", "I'm a VA"],
    "implied_keywords": ["need extra income", "work from home", "side hustle", "flexible work", "remote job search"],
    "competitors": ["Fancy Hands", "Time Etc", "Belay", "Upwork"],
    "ai_response_guide": "Respond as a business owner looking to hire a reliable virtual assistant for administrative tasks",
    "buying_signals": ["available immediately", "experienced VA", "can start now", "open to part-time"],
    "excluded_keywords": ["hiring VA", "looking for virtual assistant", "need a VA", "seeking assistant", "VA position open"],
    "location": []
}}

---

### Example 7: SELLING Services (Wedding Photography)
User Input: "Looking for wedding photographers in Abuja"

Output:
{{
    "form_title": "Wedding Photographers - Abuja",
    "category_context": "Looking for wedding photographers in Abuja",
    "intent_type": "other",
    "keywords": ["wedding photographer", "I shoot weddings", "photographer available", "photography services"],
    "implied_keywords": ["getting married", "wedding planning", "engagement photos", "need pictures", "ceremony coverage"],
    "competitors": ["Kelechi Amadi-Obi", "Remi Adetiba", "George Okoro"],
    "ai_response_guide": "Respond as someone planning a wedding and looking for professional photography services",
    "buying_signals": ["available on date", "portfolio ready", "packages available", "booking now"],
    "excluded_keywords": ["looking for photographer", "need wedding photos", "ISO photographer", "where to find photographer", "photographer recommendations"],
    "location": ["Abuja"]
}}

---

### Example 8: BUYING Products (Used Cars)
User Input: "I'm buying used cars in good condition. Looking for people who want to sell their cars quickly, need cash urgently, are relocating abroad, or upgrading to a new vehicle. Interested in Toyota, Honda, and Lexus models 2010 and newer."

Output:
{{
    "form_title": "Used Car Purchases - Toyota/Honda/Lexus",
    "category_context": "I'm buying used cars in good condition. Looking for people who want to sell their cars quickly, need cash urgently, are relocating abroad, or upgrading to a new vehicle. Interested in Toyota, Honda, and Lexus models 2010 and newer.",
    "intent_type": "other",
    "keywords": ["selling my car", "car for sale", "need to sell car fast", "Toyota for sale", "Honda for sale", "Lexus for sale"],
    "implied_keywords": ["relocating abroad", "need cash urgently", "upgrading to new car", "leaving Nigeria", "financial emergency", "quick sale needed"],
    "competitors": ["Cheki", "Cars45", "Jiji", "Autochek"],
    "ai_response_guide": "Respond as a car buyer offering quick cash payment and fair prices for well-maintained vehicles",
    "buying_signals": ["urgent sale", "price negotiable", "serious buyers only", "clean papers", "available for viewing"],
    "excluded_keywords": ["looking to buy car", "ISO used car", "where to buy Toyota", "need a car", "car dealers", "want to purchase"],
    "location": []
}}

---

### Example 9: SELLING Services (Real Estate Agent)
User Input: "I'm a real estate agent in Lekki, Lagos. I'm looking for people who just got new jobs, are relocating to Lagos, or are frustrated with their current landlords. My ideal clients are young professionals aged 25-35 looking for 1-2 bedroom apartments."

Output:
{{
    "form_title": "Real Estate Leads - Lekki Apartments",
    "category_context": "I'm a real estate agent in Lekki, Lagos. I'm looking for people who just got new jobs, are relocating to Lagos, or are frustrated with their current landlords. My ideal clients are young professionals aged 25-35 looking for 1-2 bedroom apartments.",
    "intent_type": "sales",
    "keywords": ["need apartment", "looking for flat", "apartment in Lekki", "where to rent", "2 bedroom Lagos"],
    "implied_keywords": ["just got job in Lagos", "relocating to Lagos", "moving to Lekki", "bad landlord", "landlord problems", "lease ending", "looking to move"],
    "competitors": ["PropertyPro", "Private Property", "Jumia House", "ToLet"],
    "ai_response_guide": "Respond as a real estate agent offering modern apartments in Lekki with flexible payment and great amenities",
    "buying_signals": ["ready to move", "can pay rent", "viewing apartments", "need place urgently", "starting new job"],
    "excluded_keywords": ["I'm a real estate agent", "properties available", "apartment for rent", "contact me for flats", "DM for apartments", "realtor here", "I have listings"],
    "location": ["Lekki", "Lagos", "Nigeria"]
}}

---

### Example 10: RECRUITING Partners (Business Partnership)
User Input: "Looking for business partners interested in starting a food delivery service in Port Harcourt"

Output:
{{
    "form_title": "Food Delivery Partners - Port Harcourt",
    "category_context": "Looking for business partners interested in starting a food delivery service in Port Harcourt",
    "intent_type": "partnership",
    "keywords": ["business partner needed", "interested in food delivery", "startup partner", "co-founder search", "want to start business"],
    "implied_keywords": ["have capital to invest", "looking for business opportunity", "entrepreneurial", "want to be my own boss", "business ideas"],
    "competitors": ["Jumia Food", "Glovo", "Chowdeck", "Gokada"],
    "ai_response_guide": "Respond as an entrepreneur looking for committed business partners to co-found a food delivery startup",
    "buying_signals": ["have investment ready", "interested in partnership", "available to discuss", "ready to commit"],
    "excluded_keywords": ["looking for business partner", "seeking co-founder", "ISO partner for startup", "need business partner", "partner wanted"],
    "location": ["Port Harcourt"]
}}

---

### Pattern Summary:
The AI should recognize these patterns:
1. **category_context** = FULL user input preserved, not summarized
2. **keywords** = What the TARGET AUDIENCE would say/search
3. **implied_keywords** = Problems, situations, frustrations of TARGET AUDIENCE
4. **excluded_keywords** = What people ON THE OPPOSITE SIDE say (competitors, wrong audience type)
5. **location** = Extract city/region ONLY if explicitly mentioned (e.g., "Lagos", "Nigeria", "Abuja")
6. **post_age_filter** = Time range for posts:
   - "24h" = last 24 hours (if user says "today", "right now", "past day")
   - "7d" = last week (if user says "recent", "past week", "last 7 days")
   - "30d" = last month (if user says "last 30 days", "past month", "this month")
   - "3m" = last 3 months (if user says "past 3 months", "this quarter")
   - "6m" = last 6 months (if user says "past 6 months", "last half year")
   - "1y" = last year (if user says "past year", "last 12 months")
   - "all" = default (no time filter) - use if no timeframe mentioned
7. **Directionality matters**:
   - SELLER → exclude other sellers, find buyers
   - BUYER → exclude other buyers, find sellers
   - HIRING → exclude other employers, find job seekers
   - JOB SEEKING → exclude other job seekers, find employers
"""
