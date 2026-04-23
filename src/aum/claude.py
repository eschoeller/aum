import json
import time
from pathlib import Path

from .model import ProviderResult, Window

CACHE_PATH = Path.home() / ".claude" / "last_rate_limits.json"
# Claude Code persists OAuth account info (email, org, billing type) here.
# The statusline JSON it pipes to hooks deliberately omits these, so we read
# them directly at fetch time.
CLAUDE_JSON = Path.home() / ".claude.json"


def _load_account() -> tuple[str | None, str | None]:
    """Return (plan, account_display) from ~/.claude.json, or (None, None)."""
    try:
        data = json.loads(CLAUDE_JSON.read_text())
    except (OSError, json.JSONDecodeError):
        return None, None

    oauth = data.get("oauthAccount") or {}
    email = oauth.get("emailAddress")
    # No specific plan tier (Pro / Max5 / Max20 etc.) is persisted locally.
    # Anthropic exposes it only on their account API; not worth a second
    # endpoint just for a label.
    return None, email


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
