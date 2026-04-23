import json
import time
from pathlib import Path

from .model import ProviderResult, Window

CACHE_PATH = Path.home() / ".claude" / "last_rate_limits.json"


def fetch() -> ProviderResult:
    if not CACHE_PATH.exists():
        return ProviderResult(
            provider="claude",
            error=(
                f"no cache yet at {CACHE_PATH} — install the statusline hook "
                "and run one Claude Code turn"
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

    return ProviderResult(
        provider="claude",
        plan=data.get("plan"),
        account=data.get("account"),
        windows=windows,
        stale_seconds=stale_seconds,
    )
