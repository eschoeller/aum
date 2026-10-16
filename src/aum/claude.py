"""Claude plan-quota fetcher — hits the Anthropic OAuth usage API.

Authenticates with the OAuth token Claude Code stores in
``~/.claude/.credentials.json`` and hits ``api.anthropic.com/api/oauth/usage``
(the same endpoint Claude Code's HUD uses). The response contains a ``limits``
array with per-window utilization — including per-model-family scoped windows
(e.g. Fable weekly) alongside the aggregate 5h and 7d windows.

The endpoint is aggressively rate-limited (~5 requests per token window),
so successful responses are cached to ``~/.claude/last_usage.json`` and
served on 429s. Falls back to the statusline hook cache if the API is
unreachable.
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .model import ProviderResult, Window

CACHE_PATH = Path.home() / ".claude" / "last_rate_limits.json"
USAGE_CACHE_PATH = Path.home() / ".claude" / "last_usage.json"
CLAUDE_JSON = Path.home() / ".claude.json"
CLAUDE_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
# Minimum seconds between live API calls to avoid 429 storms.
CACHE_TTL = 300


def _format_plan(subscription_type: str | None, rate_limit_tier: str | None) -> str | None:
    tail = None
    if rate_limit_tier:
        tail = rate_limit_tier
        for prefix in ("default_claude_", "claude_"):
            if tail.startswith(prefix):
                tail = tail[len(prefix):]
                break
        if subscription_type and tail.startswith(f"{subscription_type}_"):
            tail = tail[len(subscription_type) + 1:]

    if subscription_type and tail:
        return f"{subscription_type} {tail}"
    return subscription_type or tail


def _load_account() -> tuple[str | None, str | None]:
    """Return (plan, account_display)."""
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


def _load_access_token() -> str | None:
    try:
        return (
            json.loads(CLAUDE_CREDENTIALS.read_text()).get("claudeAiOauth") or {}
        ).get("accessToken")
    except (OSError, json.JSONDecodeError):
        return None


def _iso_to_unix(iso: str) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


_LABEL_MAP = {
    "session": "5h window",
    "weekly_all": "7d window",
}


def _parse_limits(limits: list[dict]) -> list[Window]:
    """Parse the ``limits`` array into Window objects."""
    windows: list[Window] = []
    for lim in limits:
        kind = lim.get("kind", "")
        pct = float(lim.get("percent", 0))
        resets_at = _iso_to_unix(lim.get("resets_at"))

        if kind in _LABEL_MAP:
            label = _LABEL_MAP[kind]
        elif kind == "weekly_scoped":
            scope = lim.get("scope") or {}
            model = (scope.get("model") or {}).get("display_name")
            if model:
                label = f"7d {model}"
            else:
                continue
        else:
            continue

        windows.append(Window(label=label, used_percent=pct, resets_at=resets_at))
    return windows


def _parse_legacy(data: dict) -> list[Window]:
    """Parse old-style five_hour / seven_day top-level keys."""
    windows: list[Window] = []
    for key, label in (("five_hour", "5h window"), ("seven_day", "7d window")):
        block = data.get(key)
        if not block:
            continue
        pct = block.get("utilization") or block.get("used_percentage") or 0
        resets_at = _iso_to_unix(block.get("resets_at")) or block.get("resets_at")
        if isinstance(resets_at, str):
            resets_at = _iso_to_unix(resets_at)
        windows.append(Window(label=label, used_percent=float(pct), resets_at=resets_at))
    return windows


def _save_usage_cache(data: dict) -> None:
    tmp = USAGE_CACHE_PATH.with_suffix(".json.tmp")
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    tmp.write_text(json.dumps(payload))
    tmp.replace(USAGE_CACHE_PATH)


def _load_usage_cache() -> tuple[dict | None, int | None]:
    """Return (cached_data, stale_seconds) or (None, None)."""
    if not USAGE_CACHE_PATH.exists():
        return None, None
    try:
        raw = json.loads(USAGE_CACHE_PATH.read_text())
        captured = raw.get("captured_at")
        stale = None
        if captured:
            ts = datetime.fromisoformat(captured.replace("Z", "+00:00")).timestamp()
            stale = max(0, int(time.time() - ts))
        return raw.get("data"), stale
    except (OSError, json.JSONDecodeError, ValueError):
        return None, None


def _result_from_usage(data: dict, stale_seconds: int | None = None) -> ProviderResult | None:
    """Build a ProviderResult from usage API data."""
    # Prefer the rich ``limits`` array; fall back to top-level keys.
    limits = data.get("limits")
    if limits:
        windows = _parse_limits(limits)
    else:
        windows = _parse_legacy(data)

    if not windows:
        return None

    plan, account = _load_account()
    return ProviderResult(
        provider="claude",
        plan=plan,
        account=account,
        windows=windows,
        stale_seconds=stale_seconds,
    )


def _fetch_live(access_token: str) -> dict | None:
    """Hit the OAuth usage API and return the raw response dict."""
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
            "User-Agent": "aum/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _fetch_statusline_cache() -> ProviderResult:
    """Fall back to the statusline hook cache."""
    if not CACHE_PATH.exists() or CACHE_PATH.stat().st_size == 0:
        return ProviderResult(
            provider="claude",
            error=(
                f"no cache at {CACHE_PATH} — run a Claude Code turn "
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
        plan=fresh_plan or cached_plan,
        account=fresh_account or cached_account,
        windows=windows,
        stale_seconds=stale_seconds,
    )


def fetch() -> ProviderResult:
    access_token = _load_access_token()

    # Check the usage cache — serve it if fresh enough to avoid 429 storms.
    cached_data, cached_stale = _load_usage_cache()
    if cached_data and cached_stale is not None and cached_stale < CACHE_TTL:
        result = _result_from_usage(cached_data, stale_seconds=cached_stale)
        if result:
            return result

    # Try the live API.
    if access_token:
        try:
            data = _fetch_live(access_token)
            if data:
                _save_usage_cache(data)
                result = _result_from_usage(data)
                if result:
                    return result
        except urllib.error.HTTPError as e:
            if e.code == 429 and cached_data:
                result = _result_from_usage(cached_data, stale_seconds=cached_stale)
                if result:
                    return result
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError):
            pass

    # Serve stale usage cache if available.
    if cached_data:
        result = _result_from_usage(cached_data, stale_seconds=cached_stale)
        if result:
            return result

    # Last resort: statusline hook cache (5h/7d only).
    return _fetch_statusline_cache()
