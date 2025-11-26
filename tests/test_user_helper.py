import pytest
from unittest.mock import AsyncMock, patch
from app.core.helpers.user_helper import UserHelper


class TestUserHelperGetUserEmail:
    """Test cases for UserHelper.get_user_email() graceful error handling"""

    @pytest.mark.asyncio
    async def test_get_user_email_success(self):
        """Test successful user email retrieval"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = {"email": "test@example.com", "name": "Test User"}

            result = await UserHelper.get_user_email("user123")

            assert result == "test@example.com"
            mock_get_user.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_user_email_with_empty_email(self):
        """Test returns empty string when email field is empty"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = {"email": "", "name": "Test User"}

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_user_not_found(self):
        """Test returns empty string when user is None"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_logs_warning_for_missing_user(self, caplog):
        """Test logs warning when user not found"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None

            await UserHelper.get_user_email("user123")

            assert "User not found for user_id: user123" in caplog.text
            assert "WARNING" in caplog.text

    @pytest.mark.asyncio
    async def test_get_user_email_service_exception(self):
        """Test returns empty string on service exception"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = Exception("Service unavailable")

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_logs_error_on_exception(self, caplog):
        """Test logs error on exception"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = Exception("Connection timeout")

            await UserHelper.get_user_email("user123")

            assert "Failed to fetch user email for user_id user123" in caplog.text
            assert "Connection timeout" in caplog.text
            assert "ERROR" in caplog.text

    @pytest.mark.asyncio
    async def test_get_user_email_missing_email_field(self):
        """Test handles user object without email field"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = {"name": "John Doe", "id": "123"}

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_network_error(self):
        """Test handles network errors gracefully"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = ConnectionError("Network unreachable")

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_timeout_error(self):
        """Test handles timeout errors gracefully"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = TimeoutError("Request timed out")

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_attribute_error(self):
        """Test handles AttributeError when user object is malformed"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = "not_a_dict"  # Invalid type

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_key_error(self):
        """Test handles KeyError gracefully when accessing email field"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            # Return dict without email key, but get() should handle it
            mock_get_user.return_value = {"user_id": "123"}

            result = await UserHelper.get_user_email("user123")

            assert result == ""

    @pytest.mark.asyncio
    async def test_get_user_email_with_none_email_value(self):
        """Test handles None value in email field"""
        with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                   new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = {"email": None, "name": "Test"}

            result = await UserHelper.get_user_email("user123")

            # get() with default "" should handle None
            assert result == "" or result is None

    @pytest.mark.asyncio
    async def test_get_user_email_does_not_crash_system(self):
        """Test that function never raises exceptions (critical for production)"""
        test_scenarios = [
            None,  # User not found
            Exception("Random error"),  # Generic exception
            ConnectionError("Network error"),  # Network failure
            TimeoutError("Timeout"),  # Timeout
            ValueError("Invalid data"),  # Data error
        ]

        for scenario in test_scenarios:
            with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                       new_callable=AsyncMock) as mock_get_user:
                if isinstance(scenario, Exception):
                    mock_get_user.side_effect = scenario
                else:
                    mock_get_user.return_value = scenario

                # Should not raise any exception
                try:
                    result = await UserHelper.get_user_email("user123")
                    assert isinstance(result, str) or result is None
                except Exception as e:
                    pytest.fail(f"get_user_email raised unexpected exception: {e}")

    @pytest.mark.asyncio
    async def test_get_user_email_multiple_users(self):
        """Test function works correctly for multiple different users"""
        users = {
            "user1": {"email": "user1@example.com"},
            "user2": {"email": "user2@example.com"},
            "user3": None,  # User not found
            "user4": {"email": "user4@example.com"},
        }

        for user_id, user_data in users.items():
            with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                       new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = user_data

                result = await UserHelper.get_user_email(user_id)

                if user_data is None:
                    assert result == ""
                else:
                    assert result == user_data.get("email", "")

    @pytest.mark.asyncio
    async def test_get_user_email_preserves_email_format(self):
        """Test function returns email in original format"""
        test_emails = [
            "simple@example.com",
            "user.name+tag@example.co.uk",
            "test_email@subdomain.example.com",
            "123numbers@example.com",
        ]

        for email in test_emails:
            with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                       new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = {"email": email}

                result = await UserHelper.get_user_email("user123")

                assert result == email

    @pytest.mark.asyncio
    async def test_get_user_email_with_special_characters_in_user_id(self):
        """Test function handles user IDs with special characters"""
        special_user_ids = [
            "user-123",
            "user_456",
            "user.789",
            "user@special",
            "user#hash",
        ]

        for user_id in special_user_ids:
            with patch('app.core.helpers.user_helper.UriBackendService.get_user_details',
                       new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = {"email": "test@example.com"}

                result = await UserHelper.get_user_email(user_id)

                assert result == "test@example.com"
                mock_get_user.assert_called_with(user_id)
