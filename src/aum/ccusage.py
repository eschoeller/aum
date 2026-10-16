"""ccusage provider — per-model usage from local ccusage-history files.

The ``ccusage`` CLI (https://github.com/ryoppippi/ccusage) parses Claude Code
session logs and writes daily/weekly/monthly JSON summaries to
``~/.claude/ccusage-history/``. Each file contains per-model token and cost
breakdowns — exactly the data needed to answer "how much Fable am I using?"

This provider reads those files (no network call) and returns one ``Window``
per model, sorted by cost descending, with the bar representing each model's
share of total cost for the period.
"""

import json
from datetime import date
from pathlib import Path

from .model import ProviderResult, Window

HISTORY_DIR = Path.home() / ".claude" / "ccusage-history"

VALID_PERIODS = ("daily", "weekly", "monthly")


def _humanize_model(model_id: str) -> str:
    """'claude-opus-4-6' -> 'opus 4.6', 'claude-fable-5-1' -> 'fable 5.1'."""
    name = model_id
    if name.startswith("claude-"):
        name = name[len("claude-"):]

    parts = name.split("-")
    # Strip date suffix like 20251001
    if parts and len(parts[-1]) >= 8 and parts[-1].isdigit():
        parts = parts[:-1]

    # Separate family from version: ['opus', '4', '6'] -> 'opus 4.6'
    family = []
    version = []
    for p in parts:
        if p.isdigit() and family:
            version.append(p)
        else:
            if version:
                family.append(".".join(version))
                version = []
            family.append(p)
    if version:
        family.append(".".join(version))

    return " ".join(family)


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def fetch(*, period: str = "daily", model_filter: str | None = None) -> ProviderResult:
    if period not in VALID_PERIODS:
        return ProviderResult(provider="ccusage", error=f"invalid period: {period}")

    if not HISTORY_DIR.exists():
        return ProviderResult(
            provider="ccusage",
            error=f"{HISTORY_DIR} not found — install ccusage and run it once",
        )

    today = date.today().isoformat()
    path = HISTORY_DIR / f"{today}.{period}.json"

    if not path.exists():
        candidates = sorted(HISTORY_DIR.glob(f"*.{period}.json"), reverse=True)
        if not candidates:
            return ProviderResult(
                provider="ccusage",
                error=f"no {period} data files in {HISTORY_DIR}",
            )
        path = candidates[0]

    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return ProviderResult(provider="ccusage", error=f"unreadable: {e}")

    entries = data.get(period) or []
    if not entries:
        return ProviderResult(provider="ccusage", error=f"no {period} entries in {path.name}")

    entry = entries[0]
    breakdowns = entry.get("modelBreakdowns") or []
    if not breakdowns:
        return ProviderResult(
            provider="ccusage",
            plan=period,
            account=entry.get("period"),
            error="no model breakdowns in most recent entry",
        )

    total_cost = entry.get("totalCost") or sum(b.get("cost", 0) for b in breakdowns)

    if model_filter:
        needle = model_filter.lower()
        breakdowns = [
            b for b in breakdowns
            if needle in (b.get("modelName") or "").lower()
            or needle in _humanize_model(b.get("modelName", "")).lower()
        ]

    windows: list[Window] = []
    for b in sorted(breakdowns, key=lambda x: x.get("cost", 0), reverse=True):
        model = _humanize_model(b.get("modelName", "?"))
        cost = b.get("cost", 0)
        cost_pct = (cost / total_cost * 100) if total_cost > 0 else 0

        output_tok = b.get("outputTokens", 0)
        extra = f"${cost:,.2f}  {_fmt_tokens(output_tok)} out"

        windows.append(Window(label=model, used_percent=cost_pct, extra=extra))

    return ProviderResult(
        provider="ccusage",
        plan=f"{period}  ${total_cost:,.2f}",
        account=entry.get("period"),
        windows=windows,
    )
