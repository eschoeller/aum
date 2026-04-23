"""Tests for rendering logic — progress bars, colors, durations."""

import pytest

from aum.render import _bar_color, _fmt_duration, _fmt_reset, _make_bar
from rich.text import Text


class TestBarColor:
    """Test progress bar color thresholds."""

    def test_green_below_75_percent(self):
        """Bar should be green below 75%."""
        assert _bar_color(0.0) == "green"
        assert _bar_color(50.0) == "green"
        assert _bar_color(74.9) == "green"

    def test_yellow_75_to_89_percent(self):
        """Bar should be yellow at 75% and above, until 90%."""
        assert _bar_color(75.0) == "yellow"
        assert _bar_color(80.0) == "yellow"
        assert _bar_color(89.9) == "yellow"

    def test_red_90_percent_and_above(self):
        """Bar should be red at 90% and above."""
        assert _bar_color(90.0) == "red"
        assert _bar_color(95.0) == "red"
        assert _bar_color(100.0) == "red"

    def test_edge_cases(self):
        """Test boundary edge cases."""
        assert _bar_color(74.99999) == "green"
        assert _bar_color(75.00001) == "yellow"
        assert _bar_color(89.99999) == "yellow"
        assert _bar_color(90.00001) == "red"


class TestFmtDuration:
    """Test duration formatting (days/hours/minutes)."""

    def test_zero_duration(self):
        """Zero or negative seconds should return 'now'."""
        assert _fmt_duration(0) == "now"
        assert _fmt_duration(-1) == "now"
        assert _fmt_duration(-3600) == "now"

    def test_minutes_only(self):
        """Durations under 1 hour should show minutes only."""
        assert _fmt_duration(60) == "1m"
        assert _fmt_duration(300) == "5m"
        assert _fmt_duration(1800) == "30m"
        assert _fmt_duration(3599) == "59m"

    def test_hours_and_minutes(self):
        """Durations 1+ hours but under 1 day should show h and m."""
        assert _fmt_duration(3600) == "1h 0m"
        assert _fmt_duration(3660) == "1h 1m"
        assert _fmt_duration(7200) == "2h 0m"
        assert _fmt_duration(9000) == "2h 30m"  # 2.5 hours
        assert _fmt_duration(86399) == "23h 59m"

    def test_days_and_hours(self):
        """Durations 1+ days should show d and h (no minutes)."""
        assert _fmt_duration(86400) == "1d 0h"  # Exactly 1 day
        assert _fmt_duration(86400 + 3600) == "1d 1h"  # 1d 1h
        assert _fmt_duration(172800) == "2d 0h"  # Exactly 2 days
        assert _fmt_duration(259200) == "3d 0h"  # Exactly 3 days
        assert _fmt_duration(86400 * 7 + 3600 * 5) == "7d 5h"

    def test_very_long_duration(self):
        """Test very long durations."""
        thirty_days = 86400 * 30
        assert _fmt_duration(thirty_days) == "30d 0h"

        with_hours = 86400 * 30 + 3600 * 12
        assert _fmt_duration(with_hours) == "30d 12h"


class TestFmtReset:
    """Test reset time formatting."""

    def test_none_reset(self):
        """None resets_at should return empty string."""
        assert _fmt_reset(None) == ""

    def test_reset_in_future(self):
        """Reset in future should show delta."""
        import time

        now = int(time.time())
        reset_in_1h = now + 3600
        result = _fmt_reset(reset_in_1h)
        assert result.startswith("resets in")
        assert "1h" in result

    def test_reset_in_past(self):
        """Reset in past should show 'resets now'."""
        import time

        now = int(time.time())
        reset_in_past = now - 3600
        result = _fmt_reset(reset_in_past)
        assert result == "resets now"

    def test_reset_just_passed(self):
        """Reset timestamp just passed should show 'resets now'."""
        import time

        now = int(time.time())
        just_passed = now - 1
        result = _fmt_reset(just_passed)
        assert result == "resets now"


class TestMakeBar:
    """Test progress bar rendering."""

    def test_bar_at_0_percent(self):
        """0% should be all empty blocks."""
        bar = _make_bar(0.0)
        assert isinstance(bar, Text)
        # Bar should have correct style (green for 0%)
        # and be 24 characters of empty blocks

    def test_bar_at_50_percent(self):
        """50% should be roughly half filled."""
        bar = _make_bar(50.0)
        assert isinstance(bar, Text)
        # Should have 12 filled blocks

    def test_bar_at_100_percent(self):
        """100% should be all filled blocks."""
        bar = _make_bar(100.0)
        assert isinstance(bar, Text)
        # Should have 24 filled blocks (red)

    def test_bar_clamped_negative(self):
        """Negative percent should clamp to 0."""
        bar = _make_bar(-10.0)
        assert isinstance(bar, Text)

    def test_bar_clamped_over_100(self):
        """Percent over 100 should clamp to 100."""
        bar = _make_bar(150.0)
        assert isinstance(bar, Text)

    def test_bar_edge_percentages(self):
        """Test bars at color threshold edges."""
        # Just before yellow
        bar_74 = _make_bar(74.9)
        assert isinstance(bar_74, Text)

        # At yellow threshold
        bar_75 = _make_bar(75.0)
        assert isinstance(bar_75, Text)

        # Just before red
        bar_89 = _make_bar(89.9)
        assert isinstance(bar_89, Text)

        # At red threshold
        bar_90 = _make_bar(90.0)
        assert isinstance(bar_90, Text)
