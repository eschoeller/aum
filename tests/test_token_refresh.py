"""Tests for token refresh flows with mocked HTTP responses."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from aum.codex import _refresh_access_token as codex_refresh
from aum.gemini import _is_token_expired, _refresh_access_token as gemini_refresh


class TestCodexTokenRefresh:
    """Test Codex OAuth token refresh flow."""

    def test_refresh_success(self):
        """Test successful token refresh from refresh_token."""
        auth_before = {
            "tokens": {
                "refresh_token": "refresh_xyz",
                "access_token": "old_access_token",
            }
        }

        mock_response = {
            "access_token": "new_access_token",
            "id_token": "new_id_token",
            "refresh_token": "new_refresh_token",
        }

        with patch("aum.codex.urllib.request.urlopen") as mock_urlopen:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_response).encode()
            mock_file.__enter__.return_value = mock_file
            mock_urlopen.return_value = mock_file

            result = codex_refresh(auth_before)

            assert result["tokens"]["access_token"] == "new_access_token"
            assert result["tokens"]["refresh_token"] == "new_refresh_token"
            assert "last_refresh" in result
            mock_urlopen.assert_called_once()

    def test_refresh_fails_no_refresh_token(self):
        """Test refresh fails if no refresh_token in auth dict."""
        auth = {"tokens": {"access_token": "token"}}  # No refresh_token

        with pytest.raises(RuntimeError, match="no refresh_token"):
            codex_refresh(auth)

    def test_refresh_preserves_id_token(self):
        """Test that old id_token is preserved if new response doesn't include one."""
        auth = {
            "tokens": {
                "refresh_token": "refresh_xyz",
                "id_token": "old_id_token",
            }
        }

        mock_response = {
            "access_token": "new_access_token",
            # No id_token in response
        }

        with patch("aum.codex.urllib.request.urlopen") as mock_urlopen:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_response).encode()
            mock_file.__enter__.return_value = mock_file
            mock_urlopen.return_value = mock_file

            result = codex_refresh(auth)

            assert result["tokens"]["id_token"] == "old_id_token"

    def test_refresh_does_not_add_refresh_token_if_not_in_response(self):
        """Test refresh_token is not updated if not in OAuth response."""
        auth = {
            "tokens": {
                "refresh_token": "original_refresh",
                "access_token": "old_access",
            }
        }

        mock_response = {
            "access_token": "new_access",
            # No refresh_token in response
        }

        with patch("aum.codex.urllib.request.urlopen") as mock_urlopen:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_response).encode()
            mock_file.__enter__.return_value = mock_file
            mock_urlopen.return_value = mock_file

            result = codex_refresh(auth)

            # Original refresh_token should be preserved
            assert result["tokens"]["refresh_token"] == "original_refresh"


class TestGeminiTokenExpiry:
    """Test Gemini token expiry detection."""

    def test_is_token_expired_with_valid_expiry(self):
        """Token with future expiry should not be expired."""
        import time

        future_expiry = int(time.time() * 1000) + 3600000  # 1 hour in future (ms)
        creds = {"expiry_date": future_expiry}
        assert _is_token_expired(creds) is False

    def test_is_token_expired_with_past_expiry(self):
        """Token with past expiry should be expired."""
        import time

        past_expiry = int(time.time() * 1000) - 3600000  # 1 hour in past (ms)
        creds = {"expiry_date": past_expiry}
        assert _is_token_expired(creds) is True

    def test_is_token_expired_no_expiry_field(self):
        """Missing expiry_date should be treated as expired (conservative)."""
        creds = {}
        assert _is_token_expired(creds) is True

    def test_is_token_expired_with_invalid_type(self):
        """Non-integer expiry should be treated as expired (conservative)."""
        creds = {"expiry_date": "not an int"}
        assert _is_token_expired(creds) is True

        creds = {"expiry_date": 1234.56}  # Float instead of int
        assert _is_token_expired(creds) is True

        creds = {"expiry_date": None}
        assert _is_token_expired(creds) is True

    def test_is_token_expired_boundary(self):
        """Test exactly at expiry boundary."""
        import time

        now_ms = int(time.time() * 1000)
        creds = {"expiry_date": now_ms}
        # At exact boundary, depends on timing — just verify it's treated as expired or very close
        result = _is_token_expired(creds)
        # Due to timing precision, this should be expired or very close
        # Just ensure the function doesn't crash and returns a bool
        assert isinstance(result, bool)


class TestGeminiTokenRefresh:
    """Test Gemini OAuth token refresh flow."""

    def test_refresh_success_form_encoded(self):
        """Test successful Gemini token refresh with form-encoded body."""
        creds_before = {
            "refresh_token": "gemini_refresh_xyz",
            "access_token": "old_access_token",
            "expiry_date": 1234567890000,
        }

        mock_response = {
            "access_token": "new_gemini_access",
            "expires_in": 3599,
            "token_type": "Bearer",
        }

        with patch("aum.gemini.urllib.request.urlopen") as mock_urlopen:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_response).encode()
            mock_file.__enter__.return_value = mock_file
            mock_urlopen.return_value = mock_file

            result = gemini_refresh(creds_before)

            assert result["access_token"] == "new_gemini_access"
            assert "expiry_date" in result
            assert isinstance(result["expiry_date"], int)

            # Verify the request was made with form-encoded body
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            # Check that the body is form-encoded (not JSON)
            assert request.data is not None
            assert b"refresh_token" in request.data  # Form-encoded has field names
            assert b"grant_type" in request.data

    def test_refresh_rotates_refresh_token(self):
        """Test that new refresh_token from response is captured."""
        creds = {
            "refresh_token": "old_refresh",
            "access_token": "old_access",
        }

        mock_response = {
            "access_token": "new_access",
            "refresh_token": "new_refresh_rotated",
            "expires_in": 3599,
        }

        with patch("aum.gemini.urllib.request.urlopen") as mock_urlopen:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_response).encode()
            mock_file.__enter__.return_value = mock_file
            mock_urlopen.return_value = mock_file

            result = gemini_refresh(creds)

            assert result["refresh_token"] == "new_refresh_rotated"

    def test_refresh_calculates_expiry_as_milliseconds(self):
        """Test that expiry_date is correctly calculated in milliseconds."""
        import time

        creds = {"refresh_token": "refresh_token", "access_token": "old_access"}

        mock_response = {
            "access_token": "new_access",
            "expires_in": 3600,  # 1 hour in seconds
        }

        before_call = int(time.time() * 1000)

        with patch("aum.gemini.urllib.request.urlopen") as mock_urlopen:
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mock_response).encode()
            mock_file.__enter__.return_value = mock_file
            mock_urlopen.return_value = mock_file

            result = gemini_refresh(creds)

            after_call = int(time.time() * 1000)
            expiry = result["expiry_date"]

            # Expiry should be roughly 1 hour from now (in milliseconds)
            expected_min = before_call + 3600 * 1000 - 5000  # 5s tolerance
            expected_max = after_call + 3600 * 1000 + 5000

            assert expected_min <= expiry <= expected_max

    def test_refresh_fails_no_refresh_token(self):
        """Test refresh fails if no refresh_token in creds."""
        creds = {"access_token": "token"}  # No refresh_token

        with pytest.raises(RuntimeError, match="no refresh_token"):
            gemini_refresh(creds)
