import pytest
from pydantic import ValidationError
from app.domain.schemas.leadform_schema import PlatformConfig, LeadFormBase
from app.domain.enums.leadform_enum import LeadFormTypeEnum


class TestPlatformConfig:
    """Test cases for PlatformConfig model validation"""

    def test_platform_config_valid_data(self):
        """Test PlatformConfig accepts valid data with all fields"""
        config = PlatformConfig(
            platform="TWITTER",
            enabled=True,
            min_followers=1000,
            exclude_retweets=True,
            verified_only=False,
            content_types=["tweets", "replies"]
        )
        assert config.platform == "TWITTER"
        assert config.enabled is True
        assert config.min_followers == 1000
        assert config.exclude_retweets is True
        assert config.verified_only is False
        assert config.content_types == ["tweets", "replies"]

    def test_platform_config_required_fields_only(self):
        """Test PlatformConfig works with only required fields"""
        config = PlatformConfig(platform="TWITTER", enabled=True)
        assert config.platform == "TWITTER"
        assert config.enabled is True
        assert config.min_followers is None
        assert config.exclude_retweets is None
        assert config.verified_only is None
        assert config.content_types is None

    def test_platform_config_missing_required_fields(self):
        """Test PlatformConfig raises error when required fields are missing"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig()

        errors = exc_info.value.errors()
        error_fields = [error['loc'][0] for error in errors]
        assert 'platform' in error_fields
        assert 'enabled' in error_fields

    def test_platform_config_missing_platform_field(self):
        """Test PlatformConfig raises error when platform is missing"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig(enabled=True)

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'platform' for error in errors)

    def test_platform_config_missing_enabled_field(self):
        """Test PlatformConfig raises error when enabled is missing"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig(platform="TWITTER")

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'enabled' for error in errors)

    def test_platform_config_forbids_extra_fields(self):
        """Test PlatformConfig rejects unknown fields (extra='forbid')"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig(
                platform="TWITTER",
                enabled=True,
                unknown_field="should_fail"
            )

        errors = exc_info.value.errors()
        assert any('extra' in str(error) or 'unknown_field' in str(error['loc'])
                  for error in errors)

    def test_platform_config_invalid_enabled_type(self):
        """Test PlatformConfig validates enabled field type"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig(
                platform="TWITTER",
                enabled="not_a_boolean"
            )

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'enabled' for error in errors)

    def test_platform_config_invalid_min_followers_type(self):
        """Test PlatformConfig validates min_followers field type"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig(
                platform="TWITTER",
                enabled=True,
                min_followers="not_an_integer"
            )

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'min_followers' for error in errors)

    def test_platform_config_invalid_content_types(self):
        """Test PlatformConfig validates content_types as list"""
        with pytest.raises(ValidationError) as exc_info:
            PlatformConfig(
                platform="TWITTER",
                enabled=True,
                content_types="not_a_list"
            )

        errors = exc_info.value.errors()
        assert any(error['loc'][0] == 'content_types' for error in errors)

    def test_platform_config_different_platforms(self):
        """Test PlatformConfig accepts different platform names"""
        platforms = ["TWITTER", "LINKEDIN", "FACEBOOK", "INSTAGRAM", "THREADS"]
        for platform_name in platforms:
            config = PlatformConfig(platform=platform_name, enabled=True)
            assert config.platform == platform_name

    def test_platform_config_enabled_false(self):
        """Test PlatformConfig accepts enabled=False"""
        config = PlatformConfig(platform="TWITTER", enabled=False)
        assert config.enabled is False

    def test_platform_config_empty_content_types(self):
        """Test PlatformConfig accepts empty content_types list"""
        config = PlatformConfig(
            platform="TWITTER",
            enabled=True,
            content_types=[]
        )
        assert config.content_types == []


class TestLeadFormBaseWithPlatformConfigs:
    """Test cases for LeadFormBase with platform configuration fields"""

    def test_lead_form_base_with_platform_configs(self):
        """Test LeadFormBase accepts platform_configs field"""
        form = LeadFormBase(
            form_type=LeadFormTypeEnum.CONVERSATIONAL,
            form_title="Test Form",
            user_id="user123",
            enable_realtime=True,
            monitoring_platforms=["TWITTER", "LINKEDIN"],
            platform_configs=[
                PlatformConfig(platform="TWITTER", enabled=True, min_followers=500),
                PlatformConfig(platform="LINKEDIN", enabled=True, verified_only=True)
            ]
        )
        assert form.enable_realtime is True
        assert form.monitoring_platforms == ["TWITTER", "LINKEDIN"]
        assert len(form.platform_configs) == 2
        assert form.platform_configs[0].platform == "TWITTER"
        assert form.platform_configs[0].min_followers == 500
        assert form.platform_configs[1].platform == "LINKEDIN"
        assert form.platform_configs[1].verified_only is True

    def test_lead_form_base_without_platform_configs(self):
        """Test LeadFormBase works without platform_configs (backward compatibility)"""
        form = LeadFormBase(
            form_type=LeadFormTypeEnum.CONVERSATIONAL,
            form_title="Test Form",
            user_id="user123"
        )
        assert form.enable_realtime is False
        assert form.monitoring_platforms is None
        assert form.platform_configs is None

    def test_lead_form_base_enable_realtime_default(self):
        """Test LeadFormBase has enable_realtime default value of False"""
        form = LeadFormBase(
            form_type=LeadFormTypeEnum.CONVERSATIONAL,
            form_title="Test Form",
            user_id="user123"
        )
        assert form.enable_realtime is False

    def test_lead_form_base_empty_platform_configs(self):
        """Test LeadFormBase accepts empty platform_configs list"""
        form = LeadFormBase(
            form_type=LeadFormTypeEnum.CONVERSATIONAL,
            form_title="Test Form",
            user_id="user123",
            enable_realtime=True,
            monitoring_platforms=[],
            platform_configs=[]
        )
        assert form.enable_realtime is True
        assert form.monitoring_platforms == []
        assert form.platform_configs == []

    def test_lead_form_base_single_platform_config(self):
        """Test LeadFormBase with single platform configuration"""
        form = LeadFormBase(
            form_type=LeadFormTypeEnum.CONVERSATIONAL,
            form_title="Test Form",
            user_id="user123",
            enable_realtime=True,
            monitoring_platforms=["TWITTER"],
            platform_configs=[
                PlatformConfig(
                    platform="TWITTER",
                    enabled=True,
                    min_followers=1000,
                    exclude_retweets=True,
                    verified_only=False
                )
            ]
        )
        assert len(form.platform_configs) == 1
        assert form.platform_configs[0].platform == "TWITTER"
        assert form.platform_configs[0].min_followers == 1000

    def test_lead_form_base_multiple_platform_configs(self):
        """Test LeadFormBase with multiple platform configurations"""
        form = LeadFormBase(
            form_type=LeadFormTypeEnum.CONVERSATIONAL,
            form_title="Test Form",
            user_id="user123",
            enable_realtime=True,
            monitoring_platforms=["TWITTER", "LINKEDIN", "FACEBOOK"],
            platform_configs=[
                PlatformConfig(platform="TWITTER", enabled=True, min_followers=500),
                PlatformConfig(platform="LINKEDIN", enabled=True, verified_only=True),
                PlatformConfig(platform="FACEBOOK", enabled=False)
            ]
        )
        assert len(form.platform_configs) == 3
        platform_names = [config.platform for config in form.platform_configs]
        assert "TWITTER" in platform_names
        assert "LINKEDIN" in platform_names
        assert "FACEBOOK" in platform_names

    def test_lead_form_base_with_other_lead_types(self):
        """Test platform_configs work with different lead form types"""
        for form_type in [LeadFormTypeEnum.CONVERSATIONAL, LeadFormTypeEnum.BUSINESS,
                          LeadFormTypeEnum.PERSON, LeadFormTypeEnum.ORGANIZATION]:
            form = LeadFormBase(
                form_type=form_type,
                form_title=f"Test {form_type} Form",
                user_id="user123",
                enable_realtime=True,
                platform_configs=[
                    PlatformConfig(platform="TWITTER", enabled=True)
                ]
            )
            assert form.enable_realtime is True
            assert len(form.platform_configs) == 1

    def test_lead_form_base_invalid_platform_config_type(self):
        """Test LeadFormBase rejects invalid platform_configs type"""
        with pytest.raises(ValidationError):
            LeadFormBase(
                form_type=LeadFormTypeEnum.CONVERSATIONAL,
                form_title="Test Form",
                user_id="user123",
                platform_configs="not_a_list"  # Should be list
            )

    def test_lead_form_base_invalid_platform_config_item(self):
        """Test LeadFormBase rejects invalid items in platform_configs"""
        with pytest.raises(ValidationError):
            LeadFormBase(
                form_type=LeadFormTypeEnum.CONVERSATIONAL,
                form_title="Test Form",
                user_id="user123",
                platform_configs=[
                    {"platform": "TWITTER"}  # Missing 'enabled' field
                ]
            )
