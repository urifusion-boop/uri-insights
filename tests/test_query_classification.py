"""
Unit tests for Query Classification Service

Tests classification logic against examples from the PRD:
- Structured Company Searches → Apollo only
- Local Business Searches → Google Maps only
- Hybrid Searches → Both sources
"""

import pytest
from app.services.QueryClassificationService import (
    QueryClassificationService,
    QueryRouteType,
)


class TestStructuredCompanyQueries:
    """Test queries that should route to Apollo only (structured companies)"""

    def test_fintech_query(self):
        result = QueryClassificationService.classify_query("Find fintechs in Lagos")
        assert result.route_type == QueryRouteType.STRUCTURED
        assert result.location == "Lagos"
        assert "fintechs" in result.keywords or "fintech" in [k.lower() for k in result.keywords]

    def test_health_startup_query(self):
        result = QueryClassificationService.classify_query("Find health startups in Nairobi")
        assert result.route_type == QueryRouteType.STRUCTURED
        assert result.location == "Nairobi"

    def test_edtech_query(self):
        result = QueryClassificationService.classify_query("Find edtech companies in Abuja")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_ai_startup_query(self):
        result = QueryClassificationService.classify_query("Find AI startups in Accra")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_marketing_agency_query(self):
        result = QueryClassificationService.classify_query("Find marketing agencies in Lagos")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_logistics_company_query(self):
        result = QueryClassificationService.classify_query("Find logistics companies in Ibadan")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_software_company_query(self):
        result = QueryClassificationService.classify_query("Find software companies in Nairobi")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_saas_startup_query(self):
        result = QueryClassificationService.classify_query("Find SaaS startups in Lagos")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_consulting_firm_query(self):
        result = QueryClassificationService.classify_query("Find consulting firms in Accra")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_digital_agency_query(self):
        result = QueryClassificationService.classify_query("Find digital marketing agencies in Abuja")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_blockchain_startup_query(self):
        result = QueryClassificationService.classify_query("Find blockchain startups in Lagos")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_cybersecurity_query(self):
        result = QueryClassificationService.classify_query("Find cybersecurity companies in Nairobi")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_venture_backed_query(self):
        result = QueryClassificationService.classify_query("Find venture-backed startups in Lagos")
        assert result.route_type == QueryRouteType.STRUCTURED

    def test_b2b_saas_query(self):
        result = QueryClassificationService.classify_query("Find B2B SaaS companies in Accra")
        assert result.route_type == QueryRouteType.STRUCTURED


class TestLocalBusinessQueries:
    """Test queries that should route to Google Maps only (local businesses)"""

    def test_coworking_space_query(self):
        result = QueryClassificationService.classify_query("Find coworking spaces in Abuja")
        assert result.route_type == QueryRouteType.LOCAL
        assert result.location == "Abuja"

    def test_pos_agent_query(self):
        result = QueryClassificationService.classify_query("Find POS agents in Accra")
        assert result.route_type == QueryRouteType.LOCAL

    def test_restaurant_query(self):
        result = QueryClassificationService.classify_query("Find restaurants in Lagos")
        assert result.route_type == QueryRouteType.LOCAL

    def test_bar_query(self):
        result = QueryClassificationService.classify_query("Find bars in Nairobi")
        assert result.route_type == QueryRouteType.LOCAL

    def test_salon_query(self):
        result = QueryClassificationService.classify_query("Find salons in Abuja")
        assert result.route_type == QueryRouteType.LOCAL

    def test_supermarket_query(self):
        result = QueryClassificationService.classify_query("Find supermarkets in Ibadan")
        assert result.route_type == QueryRouteType.LOCAL

    def test_gym_query(self):
        result = QueryClassificationService.classify_query("Find gyms in Lagos")
        assert result.route_type == QueryRouteType.LOCAL

    def test_pharmacy_query(self):
        result = QueryClassificationService.classify_query("Find pharmacies in Abuja")
        assert result.route_type == QueryRouteType.LOCAL

    def test_car_repair_query(self):
        result = QueryClassificationService.classify_query("Find car repair shops in Nairobi")
        assert result.route_type == QueryRouteType.LOCAL

    def test_cafe_query(self):
        result = QueryClassificationService.classify_query("Find cafes in Accra")
        assert result.route_type == QueryRouteType.LOCAL

    def test_hotel_query(self):
        result = QueryClassificationService.classify_query("Find hotels in Lagos")
        assert result.route_type == QueryRouteType.LOCAL

    def test_laundromat_query(self):
        result = QueryClassificationService.classify_query("Find laundromats in Abuja")
        assert result.route_type == QueryRouteType.LOCAL

    def test_event_venue_query(self):
        result = QueryClassificationService.classify_query("Find event venues in Lagos")
        assert result.route_type == QueryRouteType.LOCAL

    def test_printing_shop_query(self):
        result = QueryClassificationService.classify_query("Find printing shops in Accra")
        assert result.route_type == QueryRouteType.LOCAL

    def test_beauty_salon_query(self):
        result = QueryClassificationService.classify_query("Find beauty salons in Lagos")
        assert result.route_type == QueryRouteType.LOCAL


class TestHybridQueries:
    """Test queries that should search both Apollo and Google Maps"""

    def test_hospital_query(self):
        result = QueryClassificationService.classify_query("Find hospitals in Akure")
        assert result.route_type == QueryRouteType.HYBRID
        assert result.location == "Akure"

    def test_school_query(self):
        result = QueryClassificationService.classify_query("Find schools in Lagos")
        assert result.route_type == QueryRouteType.HYBRID

    def test_real_estate_query(self):
        result = QueryClassificationService.classify_query("Find real estate companies in Abuja")
        assert result.route_type == QueryRouteType.HYBRID

    def test_construction_query(self):
        result = QueryClassificationService.classify_query("Find construction companies in Accra")
        assert result.route_type == QueryRouteType.HYBRID

    def test_law_firm_query(self):
        result = QueryClassificationService.classify_query("Find law firms in Lagos")
        assert result.route_type == QueryRouteType.HYBRID

    def test_accounting_firm_query(self):
        result = QueryClassificationService.classify_query("Find accounting firms in Abuja")
        assert result.route_type == QueryRouteType.HYBRID

    def test_insurance_query(self):
        result = QueryClassificationService.classify_query("Find insurance companies in Nairobi")
        assert result.route_type == QueryRouteType.HYBRID

    def test_bank_query(self):
        result = QueryClassificationService.classify_query("Find banks in Lagos")
        assert result.route_type == QueryRouteType.HYBRID

    def test_recruitment_agency_query(self):
        result = QueryClassificationService.classify_query("Find recruitment agencies in Accra")
        assert result.route_type == QueryRouteType.HYBRID


class TestSearchStrategyGeneration:
    """Test that correct search strategies are generated"""

    def test_structured_strategy(self):
        classification = QueryClassificationService.classify_query("Find fintechs in Lagos")
        strategy = QueryClassificationService.get_search_strategy(classification)

        assert strategy["use_apollo"] is True
        assert strategy["use_google_maps"] is False
        assert strategy["apollo_mode"] == "primary"
        assert strategy["google_maps_mode"] is None
        assert strategy["merge_results"] is False

    def test_local_strategy(self):
        classification = QueryClassificationService.classify_query("Find restaurants in Lagos")
        strategy = QueryClassificationService.get_search_strategy(classification)

        assert strategy["use_apollo"] is False
        assert strategy["use_google_maps"] is True
        assert strategy["apollo_mode"] is None
        assert strategy["google_maps_mode"] == "primary"
        assert strategy["merge_results"] is False

    def test_hybrid_strategy(self):
        classification = QueryClassificationService.classify_query("Find hospitals in Lagos")
        strategy = QueryClassificationService.get_search_strategy(classification)

        assert strategy["use_apollo"] is True
        assert strategy["use_google_maps"] is True
        assert strategy["apollo_mode"] == "primary"
        assert strategy["google_maps_mode"] == "fallback"
        assert strategy["merge_results"] is True


class TestLocationExtraction:
    """Test location extraction from various query formats"""

    def test_location_with_in(self):
        result = QueryClassificationService.classify_query("Find startups in Lagos")
        assert result.location == "Lagos"

    def test_location_with_near(self):
        result = QueryClassificationService.classify_query("Find restaurants near Nairobi")
        assert result.location == "Nairobi"

    def test_location_at_end(self):
        result = QueryClassificationService.classify_query("Find restaurants Accra")
        assert result.location == "Accra"

    def test_multi_word_location(self):
        result = QueryClassificationService.classify_query("Find hospitals in Port Harcourt")
        assert "Port" in result.location or "Harcourt" in result.location


class TestKeywordExtraction:
    """Test keyword extraction from lead form"""

    def test_with_lead_form_keywords(self):
        result = QueryClassificationService.classify_query(
            "Find companies in Lagos",
            lead_form_keywords=["fintech", "blockchain"]
        )
        # Should classify as STRUCTURED because of fintech keyword
        assert result.route_type == QueryRouteType.STRUCTURED
        assert "fintech" in [k.lower() for k in result.keywords]

    def test_with_organization_keywords(self):
        result = QueryClassificationService.classify_query(
            "Find businesses in Abuja",
            organization_keywords=["saas", "software"]
        )
        # Should classify as STRUCTURED because of software keyword
        assert result.route_type == QueryRouteType.STRUCTURED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
