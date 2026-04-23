import json
import time
from pathlib import Path

from .model import ProviderResult, Window

CACHE_PATH = Path.home() / ".claude" / "last_rate_limits.json"
# ~/.claude.json holds the OAuth account block (email, org).
# ~/.claude/.credentials.json holds the actual subscription tier.
# Both are maintained by Claude Code itself; the statusline JSON piped to
# hooks omits them, so we read them directly at fetch time.
CLAUDE_JSON = Path.home() / ".claude.json"
CLAUDE_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"


def _format_plan(subscription_type: str | None, rate_limit_tier: str | None) -> str | None:
    """Combine subscriptionType ('max') + rateLimitTier ('default_claude_max_5x')
    into a compact label like 'max 5x' or 'max 20x'. Falls back to whichever
    is available.
    """
    # Strip the common prefix and the redundant plan family.
    tail = None
    if rate_limit_tier:
        tail = rate_limit_tier
        for prefix in ("default_claude_", "claude_"):
            if tail.startswith(prefix):
                tail = tail[len(prefix) :]
                break
        # "max_5x" -> "5x" when subscriptionType already says "max"
        if subscription_type and tail.startswith(f"{subscription_type}_"):
            tail = tail[len(subscription_type) + 1 :]

    if subscription_type and tail:
        return f"{subscription_type} {tail}"
    return subscription_type or tail


def _load_account() -> tuple[str | None, str | None]:
    """Return (plan, account_display). Either may be None if the relevant file
    is missing or unreadable."""
    email = None
    try:
        email = (json.loads(CLAUDE_JSON.read_text()).get("oauthAccount") or {}).get(
            "emailAddress"
        )
    except (OSError, json.JSONDecodeError):
        pass

    plan = None
    try:
        creds = json.loads(CLAUDE_CREDENTIALS.read_text()).get("claudeAiOauth") or {}
        plan = _format_plan(creds.get("subscriptionType"), creds.get("rateLimitTier"))
    except (OSError, json.JSONDecodeError):
        pass

    return plan, email


def fetch() -> ProviderResult:
    if not CACHE_PATH.exists() or CACHE_PATH.stat().st_size == 0:
        return ProviderResult(
            provider="claude",
            error=(
                f"no cache data at {CACHE_PATH} — run a Claude Code turn "
                "so the statusline hook can populate it"
            ),
        )

    try:
        data = json.loads(CACHE_PATH.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return ProviderResult(provider="claude", error=f"cache unreadable: {e}")

    captured_at = data.get("captured_at")
    stale_seconds: int | None = None
    if captured_at:
        try:
            from datetime import datetime

            ts = datetime.fromisoformat(captured_at.replace("Z", "+00:00")).timestamp()
            stale_seconds = max(0, int(time.time() - ts))
        except ValueError:
            pass

    rate_limits = data.get("rate_limits") or {}
    windows: list[Window] = []

    for key, label in (("five_hour", "5h window"), ("seven_day", "7d window")):
        block = rate_limits.get(key)
        if not block:
            continue
        windows.append(
            Window(
                label=label,
                used_percent=float(block.get("used_percentage", 0)),
                resets_at=block.get("resets_at"),
            )
        )

    cached_plan = data.get("plan")
    cached_account = data.get("account")
    fresh_plan, fresh_account = _load_account()

    return ProviderResult(
        provider="claude",
        plan=cached_plan or fresh_plan,
        account=cached_account or fresh_account,
        windows=windows,
        stale_seconds=stale_seconds,
    )
