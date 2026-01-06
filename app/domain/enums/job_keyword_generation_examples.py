"""
Job Keyword Generation Examples

This file contains diverse examples to train the AI on how to properly generate
job role keywords from business solution descriptions. The AI should learn the PATTERN
of extracting relevant hiring signals from what a company SELLS.

Key Pattern to Learn:
1. User SELLS a solution → Find companies HIRING roles that need that solution
2. Extract domain/industry terms from input (e.g., "cloud", "marketing", "security")
3. Generate job titles containing those domain terms + standard roles
4. Include seniority variations (Junior, Senior, Lead, Principal, Chief)
5. Focus on HIRING signals, not the seller's own roles

CRITICAL: Keywords must be RELEVANT to the solution context!
If input mentions "cloud" → output MUST include cloud-related roles
If input mentions "marketing" → output MUST include marketing roles
If input mentions "security" → output MUST include security roles
"""

JOB_KEYWORD_GENERATION_EXAMPLES = """
### Example 1: Cloud Services & Infrastructure
Input: "I sell cloud services and help businesses go on the cloud"

Analysis:
- Domain terms: "cloud", "infrastructure", "migration"
- Companies hiring these roles = companies needing cloud solutions
- Include seniority variations and related specializations

Output:
{
    "job_keywords": [
        "Cloud Engineer",
        "Senior Cloud Engineer",
        "Cloud Solutions Architect",
        "Cloud Infrastructure Engineer",
        "DevOps Engineer",
        "Senior DevOps Engineer",
        "Site Reliability Engineer",
        "Platform Engineer",
        "Cloud Migration Specialist"
    ],
    "reasoning": "Companies hiring cloud engineers, DevOps engineers, and infrastructure architects are actively building or migrating to cloud infrastructure, indicating they need cloud services and support."
}

---

### Example 2: Cybersecurity Solutions
Input: "We provide enterprise cybersecurity solutions including threat detection, penetration testing, and security audits"

Analysis:
- Domain terms: "security", "cybersecurity", "threat", "compliance"
- Target companies with security hiring needs
- Include various security specializations

Output:
{
    "job_keywords": [
        "Security Engineer",
        "Cybersecurity Analyst",
        "Information Security Manager",
        "Chief Information Security Officer",
        "Security Operations Center Analyst",
        "Penetration Tester",
        "Threat Intelligence Analyst",
        "Security Architect"
    ],
    "reasoning": "Organizations hiring security professionals are actively building security infrastructure and need external cybersecurity solutions, audits, and consulting services."
}

---

### Example 3: Marketing Automation Software
Input: "We sell marketing automation software for small businesses to help them automate email campaigns, social media posting, and lead nurturing"

Analysis:
- Domain terms: "marketing", "digital marketing", "growth"
- Target businesses investing in marketing capabilities
- Include various marketing role levels

Output:
{
    "job_keywords": [
        "Marketing Manager",
        "Digital Marketing Manager",
        "Growth Marketing Manager",
        "Marketing Coordinator",
        "Marketing Director",
        "Email Marketing Specialist",
        "Marketing Automation Specialist",
        "Demand Generation Manager"
    ],
    "reasoning": "Companies hiring marketing managers and specialists are scaling their marketing operations and likely need automation tools to increase efficiency and ROI."
}

---

### Example 4: Accounting & Financial Software
Input: "We offer cloud-based accounting software for freelancers and small businesses"

Analysis:
- Domain terms: "accounting", "finance", "bookkeeping"
- Target businesses with accounting/finance needs
- Include entry to senior level roles

Output:
{
    "job_keywords": [
        "Accountant",
        "Senior Accountant",
        "Bookkeeper",
        "Finance Manager",
        "Accounting Manager",
        "Controller",
        "Financial Analyst",
        "Chief Financial Officer"
    ],
    "reasoning": "Organizations hiring accounting and finance professionals need robust financial management tools and software to handle increased complexity and scale."
}

---

### Example 5: HR Management & Recruitment Software
Input: "We provide HR software that helps companies manage payroll, benefits, employee records, and recruitment"

Analysis:
- Domain terms: "HR", "human resources", "talent", "recruitment"
- Target companies building HR infrastructure
- Include HR specializations

Output:
{
    "job_keywords": [
        "Human Resources Manager",
        "HR Business Partner",
        "Talent Acquisition Manager",
        "HR Coordinator",
        "Chief People Officer",
        "Employee Relations Manager",
        "Compensation and Benefits Manager",
        "HR Operations Manager"
    ],
    "reasoning": "Companies hiring HR professionals are scaling their workforce and need comprehensive HR management systems to handle payroll, benefits, and compliance."
}

---

### Example 6: Sales CRM & Enablement Tools
Input: "We sell CRM software and sales enablement tools to help B2B companies close more deals"

Analysis:
- Domain terms: "sales", "CRM", "business development"
- Target companies building sales teams
- Include sales leadership roles

Output:
{
    "job_keywords": [
        "Sales Manager",
        "Sales Director",
        "Vice President of Sales",
        "Business Development Manager",
        "Sales Operations Manager",
        "Account Executive",
        "Sales Enablement Manager",
        "Chief Revenue Officer"
    ],
    "reasoning": "Organizations hiring sales leaders and teams are actively investing in revenue growth and need CRM systems and sales tools to track pipelines and improve conversion rates."
}

---

### Example 7: Data Analytics & Business Intelligence
Input: "We provide data analytics and business intelligence solutions for enterprises"

Analysis:
- Domain terms: "data", "analytics", "business intelligence", "BI"
- Target data-driven companies
- Include various data roles

Output:
{
    "job_keywords": [
        "Data Analyst",
        "Senior Data Analyst",
        "Business Intelligence Analyst",
        "Data Engineer",
        "Analytics Manager",
        "Chief Data Officer",
        "Data Scientist",
        "Business Intelligence Manager"
    ],
    "reasoning": "Companies hiring data analysts and engineers are building data capabilities and need robust analytics platforms and BI tools to derive insights."
}

---

### Example 8: Customer Support & Helpdesk Software
Input: "We offer customer support software including ticketing systems, live chat, and knowledge base solutions"

Analysis:
- Domain terms: "customer support", "customer service", "helpdesk"
- Target companies scaling support operations
- Include support management roles

Output:
{
    "job_keywords": [
        "Customer Support Manager",
        "Customer Success Manager",
        "Support Operations Manager",
        "Head of Customer Support",
        "Customer Service Representative",
        "Technical Support Engineer",
        "Customer Experience Manager",
        "Support Team Lead"
    ],
    "reasoning": "Organizations hiring customer support teams are scaling their customer service operations and need helpdesk software, ticketing systems, and support tools."
}

---

### Example 9: Supply Chain & Logistics Software
Input: "We sell supply chain management software that helps businesses optimize inventory, warehousing, and logistics"

Analysis:
- Domain terms: "supply chain", "logistics", "operations", "inventory"
- Target companies with logistics needs
- Include operations and logistics roles

Output:
{
    "job_keywords": [
        "Supply Chain Manager",
        "Logistics Manager",
        "Operations Manager",
        "Inventory Manager",
        "Warehouse Manager",
        "Supply Chain Analyst",
        "Director of Operations",
        "Chief Operating Officer"
    ],
    "reasoning": "Companies hiring supply chain and logistics professionals are managing complex operations and need software to optimize inventory, reduce costs, and improve efficiency."
}

---

### Example 10: Content Management & Publishing Tools
Input: "We provide content management systems and publishing tools for media companies and content creators"

Analysis:
- Domain terms: "content", "editorial", "publishing", "media"
- Target content-focused companies
- Include editorial and content roles

Output:
{
    "job_keywords": [
        "Content Manager",
        "Content Strategist",
        "Editorial Manager",
        "Content Marketing Manager",
        "Managing Editor",
        "Content Operations Manager",
        "Chief Content Officer",
        "Digital Content Producer"
    ],
    "reasoning": "Organizations hiring content managers and editors are scaling content production and need CMS platforms and publishing tools to manage workflows efficiently."
}

---

### Example 11: Cybersecurity Training & Awareness
Input: "We offer cybersecurity training and security awareness programs for employees"

Analysis:
- Domain terms: "security", "training", "compliance", "awareness"
- Target companies investing in security culture
- Include security and training roles

Output:
{
    "job_keywords": [
        "Security Awareness Manager",
        "Information Security Manager",
        "Compliance Manager",
        "Chief Information Security Officer",
        "Training and Development Manager",
        "Security Compliance Analyst",
        "Risk Manager",
        "IT Security Manager"
    ],
    "reasoning": "Companies hiring security and compliance managers are building security-conscious cultures and need employee training programs to reduce human security risks."
}

---

### Example 12: E-commerce & Online Store Solutions
Input: "We build e-commerce platforms and online store solutions for retail businesses"

Analysis:
- Domain terms: "e-commerce", "retail", "online", "digital"
- Target retail companies going digital
- Include e-commerce and digital roles

Output:
{
    "job_keywords": [
        "E-commerce Manager",
        "Digital Commerce Manager",
        "E-commerce Director",
        "Online Store Manager",
        "E-commerce Operations Manager",
        "Digital Marketing Manager",
        "E-commerce Product Manager",
        "Head of E-commerce"
    ],
    "reasoning": "Retailers hiring e-commerce managers are expanding online and need e-commerce platforms, payment solutions, and digital store infrastructure."
}

---

### Example 13: AI & Machine Learning Solutions
Input: "We provide AI and machine learning solutions for predictive analytics and automation"

Analysis:
- Domain terms: "AI", "machine learning", "ML", "data science"
- Target companies adopting AI
- Include AI and ML specializations

Output:
{
    "job_keywords": [
        "Machine Learning Engineer",
        "AI Engineer",
        "Data Scientist",
        "Senior Machine Learning Engineer",
        "AI Research Scientist",
        "Machine Learning Manager",
        "Head of AI",
        "Chief AI Officer"
    ],
    "reasoning": "Organizations hiring ML engineers and data scientists are building AI capabilities and need ML platforms, model deployment tools, and AI infrastructure."
}

---

### Example 14: Legal Tech & Compliance Software
Input: "We sell legal technology and compliance management software for law firms and corporate legal departments"

Analysis:
- Domain terms: "legal", "compliance", "regulatory", "law"
- Target legal departments and firms
- Include legal and compliance roles

Output:
{
    "job_keywords": [
        "Legal Counsel",
        "Compliance Manager",
        "Legal Operations Manager",
        "General Counsel",
        "Regulatory Compliance Officer",
        "Chief Compliance Officer",
        "Contract Manager",
        "Legal Technology Manager"
    ],
    "reasoning": "Law firms and companies hiring legal and compliance professionals need legal tech tools for contract management, compliance tracking, and regulatory reporting."
}

---

### Example 15: Video Production & Editing Services
Input: "We offer professional video production and editing services for businesses and content creators"

Analysis:
- Domain terms: "video", "content", "media", "creative"
- Target companies investing in video content
- Include video and creative roles

Output:
{
    "job_keywords": [
        "Video Producer",
        "Video Editor",
        "Content Creator",
        "Creative Director",
        "Video Production Manager",
        "Multimedia Producer",
        "Video Marketing Manager",
        "Head of Video Production"
    ],
    "reasoning": "Companies hiring video producers and editors are scaling video content production and may need external production services, equipment, or post-production support."
}

---

### Example 16: Construction & Project Management Software
Input: "We provide construction management software for project planning, budgeting, and team collaboration"

Analysis:
- Domain terms: "construction", "project management", "building"
- Target construction companies and contractors
- Include construction management roles

Output:
{
    "job_keywords": [
        "Construction Project Manager",
        "Project Manager",
        "Construction Manager",
        "Senior Project Manager",
        "Director of Construction",
        "Project Coordinator",
        "Construction Operations Manager",
        "Chief Operations Officer"
    ],
    "reasoning": "Construction firms hiring project managers are managing complex projects and need software for planning, budgeting, scheduling, and team coordination."
}

---

### Example 17: Healthcare IT & Medical Software
Input: "We sell healthcare IT solutions including electronic health records (EHR) and practice management systems"

Analysis:
- Domain terms: "healthcare", "medical", "clinical", "health IT"
- Target healthcare organizations
- Include healthcare IT and admin roles

Output:
{
    "job_keywords": [
        "Healthcare IT Manager",
        "Clinical Informatics Specialist",
        "Health Information Manager",
        "Practice Manager",
        "Chief Medical Information Officer",
        "Healthcare Systems Administrator",
        "EHR Implementation Specialist",
        "Director of Health Information"
    ],
    "reasoning": "Healthcare organizations hiring IT and practice managers are modernizing operations and need EHR systems, practice management software, and compliance tools."
}

---

### Example 18: Graphic Design & Creative Services
Input: "We provide graphic design services for branding, marketing materials, and social media content"

Analysis:
- Domain terms: "design", "creative", "branding", "graphic"
- Target companies investing in design
- Include design and creative roles

Output:
{
    "job_keywords": [
        "Graphic Designer",
        "Senior Graphic Designer",
        "Creative Director",
        "Brand Designer",
        "Visual Designer",
        "Art Director",
        "Marketing Designer",
        "Head of Creative"
    ],
    "reasoning": "Companies hiring graphic designers and creative directors are expanding their brand presence and may need external design services or freelance support."
}

---

### Pattern Summary:
The AI should extract these patterns:

1. **Domain Term Extraction**:
   - Identify key industry/domain words: "cloud", "security", "marketing", "HR", "legal", etc.
   - Keywords MUST contain these domain terms to ensure relevance
   - Example: "cloud services" → output must include "Cloud Engineer", "Cloud Architect", etc.

2. **Relevance Validation**:
   - At least 60% of generated keywords should contain domain terms from the input
   - If input mentions "cloud" → most keywords should include "Cloud"
   - If input mentions "marketing" → most keywords should include "Marketing"
   - If input mentions "security" → most keywords should include "Security"

3. **Seniority Variations**:
   - Include junior/entry: "Junior", "Associate", "Coordinator"
   - Include mid-level: (no prefix), "Senior"
   - Include leadership: "Director", "VP", "Head of", "Chief"

4. **Role Specializations**:
   - Include specific specializations relevant to the solution
   - Example: For cloud → "DevOps", "Platform", "Site Reliability"
   - Example: For security → "Penetration Tester", "SOC Analyst", "Compliance"

5. **Hiring Signal Logic**:
   - Companies hiring these roles = companies that NEED the solution
   - If they're hiring "Cloud Engineers" → they need cloud services
   - If they're hiring "Marketing Managers" → they need marketing tools
   - If they're hiring "Security Analysts" → they need security solutions

6. **Return 5-9 job titles** for each query (not too few, not too many)
"""
