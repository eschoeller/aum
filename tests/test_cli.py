"""Tests for CLI argument parsing and provider selection logic."""

from unittest.mock import patch

import pytest

from aum.cli import _selected_providers


class TestSelectedProviders:
    """Test provider selection based on CLI arguments."""

    class Args:
        """Mock argparse.Namespace for testing."""

        def __init__(self, provider=None, gemini=False):
            self.provider = provider
            self.gemini = gemini

    def test_default_providers_no_gemini(self):
        """Default should select claude, codex, copilot (no gemini)."""
        args = self.Args(provider=None, gemini=False)
        selected = _selected_providers(args)
        assert selected == ["claude", "codex", "copilot"]

    def test_default_providers_with_gemini_flag(self):
        """--gemini flag should add gemini to defaults."""
        args = self.Args(provider=None, gemini=True)
        selected = _selected_providers(args)
        assert selected == ["claude", "codex", "copilot", "gemini"]

    def test_single_provider_selected(self):
        """Single -p flag should select that provider only."""
        args = self.Args(provider=["claude"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["claude"]

        args = self.Args(provider=["codex"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["codex"]

    def test_multiple_providers_repeatable(self):
        """Multiple -p flags should select all specified providers."""
        args = self.Args(provider=["claude", "copilot"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["claude", "copilot"]

        args = self.Args(provider=["codex", "gemini"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["codex", "gemini"]

    def test_all_four_providers(self):
        """Can select all four providers explicitly."""
        args = self.Args(provider=["claude", "codex", "copilot", "gemini"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["claude", "codex", "copilot", "gemini"]

    def test_gemini_flag_independent_of_provider_list(self):
        """--gemini flag and -p are independent; gemini flag adds to defaults."""
        # If -p is specified, but gemini=True, gemini is still added
        args = self.Args(provider=["claude"], gemini=True)
        selected = _selected_providers(args)
        # The implementation always adds gemini when gemini=True
        assert selected == ["claude", "gemini"]

    def test_empty_provider_list_uses_default(self):
        """Empty -p list should fall back to defaults."""
        args = self.Args(provider=[], gemini=False)
        selected = _selected_providers(args)
        # Empty list is falsy, so defaults apply
        assert selected == ["claude", "codex", "copilot"]

    def test_none_provider_uses_default(self):
        """None provider should use defaults."""
        args = self.Args(provider=None, gemini=False)
        selected = _selected_providers(args)
        assert selected == ["claude", "codex", "copilot"]

    def test_repeated_provider_is_deduped(self):
        """`-p codex -p codex` should collapse to a single codex entry."""
        args = self.Args(provider=["codex", "codex"], gemini=False)
        assert _selected_providers(args) == ["codex"]

    def test_dedupe_preserves_first_position(self):
        """Dedupe should keep the first occurrence's order."""
        args = self.Args(provider=["codex", "claude", "codex"], gemini=False)
        assert _selected_providers(args) == ["codex", "claude"]

    def test_gemini_flag_additive_even_when_p_supplied(self):
        """`-p claude --gemini` should fetch claude + gemini, not just claude."""
        args = self.Args(provider=["claude"], gemini=True)
        assert _selected_providers(args) == ["claude", "gemini"]

    def test_gemini_flag_noop_when_already_in_provider_list(self):
        """If gemini is already in -p list, --gemini doesn't duplicate it."""
        args = self.Args(provider=["gemini"], gemini=True)
        assert _selected_providers(args) == ["gemini"]


class TestProviderOrdering:
    """Test that providers are returned in requested order."""

    class Args:
        """Mock argparse.Namespace."""

        def __init__(self, provider=None, gemini=False):
            self.provider = provider
            self.gemini = gemini

    def test_providers_in_requested_order(self):
        """Selected providers should match the order they were requested."""
        args = self.Args(provider=["copilot", "claude", "codex"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["copilot", "claude", "codex"]

        args = self.Args(provider=["gemini", "codex"], gemini=False)
        selected = _selected_providers(args)
        assert selected == ["gemini", "codex"]

    def test_default_order_preserved(self):
        """Default providers should always be in same order."""
        args = self.Args(provider=None, gemini=False)
        selected1 = _selected_providers(args)
        selected2 = _selected_providers(args)
        assert selected1 == selected2
        assert selected1 == ["claude", "codex", "copilot"]


class TestCliArgumentValidation:
    """Test CLI argument constraints enforced by main()."""

    def test_interval_minimum_10_seconds(self, capsys):
        """--interval < 10 with --watch should exit non-zero via argparse."""
        from aum.cli import main

        with patch("sys.argv", ["aum", "--watch", "-n", "5"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        # argparse.error exits with code 2
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "interval" in err.lower() and "10" in err

    def test_watch_and_json_mutually_exclusive(self, capsys):
        """--watch and --json together should exit non-zero."""
        from aum.cli import main

        with patch("sys.argv", ["aum", "--watch", "--json"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "mutually exclusive" in err.lower()

    def test_invalid_provider_name_rejected(self, capsys):
        """argparse should reject providers not in PROVIDERS dict."""
        from aum.cli import main

        with patch("sys.argv", ["aum", "-p", "anthropic_api"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "invalid choice" in err.lower()
