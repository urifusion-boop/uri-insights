"""
Test script to verify job keyword generation improvements
Run this to test the enhanced keyword generation with domain relevance validation
"""
import asyncio
import sys
sys.path.append('/Users/apple/Desktop/URI/uri-insights')

from app.services.JobKeywordGenerationService import JobKeywordGenerationService


async def test_keyword_generation():
    """Test job keyword generation with various inputs"""

    test_cases = [
        {
            "name": "Cloud Services (Original Issue)",
            "input": "i sell cloud services and help businesses go on the cloud",
            "expected_terms": ["cloud", "devops", "platform", "infrastructure"]
        },
        {
            "name": "Marketing Automation",
            "input": "We sell marketing automation software for small businesses",
            "expected_terms": ["marketing", "growth", "digital"]
        },
        {
            "name": "Cybersecurity Solutions",
            "input": "We provide enterprise cybersecurity solutions including threat detection",
            "expected_terms": ["security", "cybersecurity"]
        },
        {
            "name": "HR Management Software",
            "input": "We provide HR software that helps companies manage payroll and recruitment",
            "expected_terms": ["hr", "human resources", "talent"]
        }
    ]

    print("=" * 80)
    print("JOB KEYWORD GENERATION - IMPROVEMENT TEST")
    print("=" * 80)
    print()

    for test_case in test_cases:
        print(f"Test: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        print("-" * 80)

        # Extract domain terms
        domain_terms = JobKeywordGenerationService._extract_domain_terms(test_case['input'])
        print(f"✓ Domain terms detected: {', '.join(domain_terms) if domain_terms else 'None'}")

        # Generate keywords
        try:
            result = await JobKeywordGenerationService.generate_job_keywords(test_case['input'])

            print(f"✓ Generated {len(result.job_keywords)} keywords:")
            for idx, keyword in enumerate(result.job_keywords, 1):
                print(f"  {idx}. {keyword}")

            print(f"\n✓ Reasoning: {result.reasoning}")

            # Validate relevance
            if domain_terms:
                matching = 0
                for keyword in result.job_keywords:
                    keyword_lower = keyword.lower()
                    for term in domain_terms:
                        if any(word in keyword_lower for word in term.split()):
                            matching += 1
                            break

                relevance_pct = (matching / len(result.job_keywords)) * 100
                print(f"\n✓ Relevance: {matching}/{len(result.job_keywords)} keywords ({relevance_pct:.0f}%) contain domain terms")

                if relevance_pct >= 50:
                    print("✅ PASS - Good keyword relevance!")
                else:
                    print("❌ FAIL - Low keyword relevance")

            print()

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            print()

        print("=" * 80)
        print()


if __name__ == "__main__":
    print("\n🚀 Starting Job Keyword Generation Tests...\n")
    asyncio.run(test_keyword_generation())
    print("✅ Tests completed!\n")
