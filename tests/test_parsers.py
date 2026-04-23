"""Tests for parser functions across all providers."""

import json
from unittest.mock import patch

import pytest

from aum.codex import _parse as codex_parse, _window_label
from aum.copilot import fetch as copilot_fetch
from aum.gemini import fetch as gemini_fetch
from aum.model import ProviderResult, Window


class TestCodexParsers:
    """Test Codex parser and window label generation."""

    def test_window_label_derives_from_seconds(self):
        """Ensure _window_label generates correct labels from duration."""
        assert _window_label(None, "fallback") == "fallback"
        assert _window_label(86400, "fallback") == "1d window"  # 1 day
        assert _window_label(259200, "fallback") == "3d window"  # 3 days
        assert _window_label(3600, "fallback") == "1h window"  # 1 hour
        assert _window_label(7200, "fallback") == "2h window"  # 2 hours
        assert _window_label(300, "fallback") == "5m window"  # 5 minutes
        assert _window_label(60, "fallback") == "1m window"  # 1 minute

    def test_window_label_non_divisible(self):
        """Non-divisible seconds get formatted as 'Xs window' fallback."""
        # 3661 seconds is not evenly divisible by 60/3600/86400, so formats as seconds
        assert _window_label(3661, "primary") == "3661s window"
        # 90001 is not divisible by 3600, formats as seconds
        assert _window_label(90001, "secondary") == "90001s window"

    def test_parse_extracts_windows(self):
        """Ensure codex _parse extracts rate limit windows correctly."""
        data = {
            "plan_type": "plus",
            "email": "user@example.com",
            "rate_limit": {
                "primary_window": {
                    "limit_window_seconds": 18000,  # 5h
                    "used_percent": 23.4,
                    "reset_at": 1730000000,
                },
                "secondary_window": {
                    "limit_window_seconds": 604800,  # 7d
                    "used_percent": 12.1,
                    "reset_at": 1730400000,
                },
            },
        }
        result = codex_parse(data)

        assert result.provider == "codex"
        assert result.plan == "plus"
        assert result.account == "user@example.com"
        assert len(result.windows) == 2

        # Check primary window
        assert result.windows[0].label == "5h window"
        assert result.windows[0].used_percent == 23.4
        assert result.windows[0].resets_at == 1730000000

        # Check secondary window
        assert result.windows[1].label == "7d window"
        assert result.windows[1].used_percent == 12.1
        assert result.windows[1].resets_at == 1730400000

    def test_parse_handles_missing_windows(self):
        """Ensure _parse gracefully handles missing rate_limit blocks."""
        data = {"plan_type": "plus", "email": "user@example.com", "rate_limit": {}}
        result = codex_parse(data)

        assert result.provider == "codex"
        assert result.plan == "plus"
        assert result.account == "user@example.com"
        assert result.windows == []
        assert result.error is None

    def test_parse_handles_missing_rate_limit(self):
        """Ensure _parse handles data with no rate_limit key."""
        data = {"plan_type": "plus", "email": "user@example.com"}
        result = codex_parse(data)

        assert result.provider == "codex"
        assert result.windows == []
        assert result.error is None

    def test_parse_used_percent_defaults_to_zero(self):
        """Ensure missing used_percent defaults to 0."""
        data = {
            "plan_type": "plus",
            "email": "user@example.com",
            "rate_limit": {
                "primary_window": {
                    "limit_window_seconds": 18000,
                    "reset_at": 1730000000,
                    # Missing used_percent
                },
            },
        }
        result = codex_parse(data)

        assert len(result.windows) == 1
        assert result.windows[0].used_percent == 0.0


class TestClaudeParsers:
    """Test Claude plan formatter."""

    def test_format_plan_with_both_subscription_and_tier(self):
        """Test combining subscriptionType and rateLimitTier."""
        from aum.claude import _format_plan

        result = _format_plan("max", "default_claude_max_5x")
        assert result == "max 5x"

        result = _format_plan("max", "default_claude_max_20x")
        assert result == "max 20x"

    def test_format_plan_with_subscription_only(self):
        """Test fallback to subscriptionType alone."""
        from aum.claude import _format_plan

        result = _format_plan("max", None)
        assert result == "max"

        result = _format_plan("plus", None)
        assert result == "plus"

    def test_format_plan_with_tier_only(self):
        """Test fallback to rateLimitTier alone."""
        from aum.claude import _format_plan

        result = _format_plan(None, "default_claude_5x")
        assert result == "5x"

    def test_format_plan_both_none(self):
        """Test None when both are missing."""
        from aum.claude import _format_plan

        result = _format_plan(None, None)
        assert result is None

    def test_format_plan_strips_redundant_prefix(self):
        """Test that redundant plan family is stripped from tier."""
        from aum.claude import _format_plan

        # "max_5x" -> "5x" when subscriptionType says "max"
        result = _format_plan("max", "claude_max_5x")
        assert result == "max 5x"

        result = _format_plan("plus", "default_claude_plus_2x")
        assert result == "plus 2x"


class TestCopilotParsers:
    """Test Copilot quota snapshot parsing (via mocked gh api subprocess)."""

    def _run_fetch(self, api_response: dict) -> ProviderResult:
        """Invoke copilot.fetch with a mocked `gh api` subprocess result."""
        completed = type(
            "CompletedProcess",
            (),
            {"returncode": 0, "stdout": json.dumps(api_response), "stderr": ""},
        )
        with patch("aum.copilot.subprocess.run", return_value=completed):
            return copilot_fetch()

    def test_copilot_quota_mixed_metered_and_unlimited(self):
        """Premium reqs are metered (shows used %), chat/completions are unlimited."""
        data = {
            "login": "alice",
            "copilot_plan": "business",
            "organization_list": [{"login": "my-org"}],
            "quota_reset_date_utc": "2026-05-01T00:00:00Z",
            "quota_snapshots": {
                "premium_interactions": {
                    "unlimited": False,
                    "entitlement": 300,
                    "remaining": 230,
                    "percent_remaining": 76.6,
                },
                "chat": {
                    "unlimited": True,
                    "entitlement": 0,
                    "remaining": 0,
                    "percent_remaining": 100.0,
                },
                "completions": {
                    "unlimited": True,
                    "entitlement": 0,
                    "remaining": 0,
                    "percent_remaining": 100.0,
                },
            },
        }
        result = self._run_fetch(data)

        assert result.provider == "copilot"
        assert result.plan == "business"
        assert result.account == "alice (my-org)"
        # premium + chat + completions
        assert len(result.windows) == 3
        premium = result.windows[0]
        assert premium.label == "premium req"
        assert abs(premium.used_percent - 23.4) < 0.01
        assert premium.extra == "70/300"
        # Both unlimited windows render at 0% used with an "unlimited" tag.
        for w in result.windows[1:]:
            assert w.used_percent == 0.0
            assert w.extra == "unlimited"

    def test_copilot_fetch_handles_gh_missing(self):
        """If gh isn't installed, fetch returns an error without raising."""
        with patch("aum.copilot.subprocess.run", side_effect=FileNotFoundError):
            result = copilot_fetch()
        assert result.provider == "copilot"
        assert "gh CLI not installed" in (result.error or "")


class TestGeminiParsers:
    """Test Gemini per-model quota parsing (via mocked HTTP)."""

    def test_gemini_model_id_strips_prefix_and_filters_unavailable(self):
        """Available Flash models render stripped of 'gemini-'; unavailable
        Pro models (epoch reset_time) are filtered out."""
        # Mock loadCodeAssist then retrieveUserQuota
        load_response = {
            "cloudaicompanionProject": "test-project",
            "currentTier": {"id": "free-tier", "name": "Code Assist for individuals"},
        }
        quota_response = {
            "buckets": [
                {
                    "modelId": "gemini-2.5-flash",
                    "remainingFraction": 0.8,
                    "resetTime": "2030-01-01T00:00:00Z",
                    "tokenType": "REQUESTS",
                },
                {
                    "modelId": "gemini-2.5-pro",
                    "remainingFraction": 0,
                    "resetTime": "1970-01-01T00:00:00Z",  # Filtered
                    "tokenType": "REQUESTS",
                },
            ],
        }

        # Both loadCodeAssist and retrieveUserQuota are _post calls in sequence
        responses = [load_response, quota_response]
        call_count = {"n": 0}

        def fake_post(url, body, token):  # noqa: ARG001
            i = call_count["n"]
            call_count["n"] += 1
            return responses[i]

        with (
            patch("aum.gemini._load_creds", return_value={"access_token": "t"}) if False
            else patch("aum.gemini._post", side_effect=fake_post),
            patch("aum.gemini.CREDS_PATH") as mock_path,
            patch("aum.gemini._load_account", return_value="user@example.com"),
        ):
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = json.dumps({"access_token": "t"})
            result = gemini_fetch()

        assert result.provider == "gemini"
        # Pro model filtered; only Flash remains
        assert len(result.windows) == 1
        assert result.windows[0].label == "2.5-flash"
        # 80% remaining = 20% used
        assert abs(result.windows[0].used_percent - 20.0) < 0.01
