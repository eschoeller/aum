"""GitHub Copilot plan-quota fetcher — piggybacks on the ``gh`` CLI.

Hits ``/copilot_internal/user`` — an undocumented but stable internal
endpoint — via ``gh api`` so we inherit whatever OAuth token ``gh auth
login`` stored in the GNOME Keyring. Works for both individual and
org-seat accounts (tested against a UCBoulder business seat).

The response exposes ``quota_snapshots`` for each metered quota
(``premium_interactions``, ``chat``, ``completions``). Quotas flagged
``unlimited`` are rendered with a 0% bar and the ``(unlimited)`` tag so
the row is visible but not alarming. Reset is monthly on the 1st UTC,
different from Claude/Codex's rolling windows.
"""

import json
import subprocess

from .model import ProviderResult, Window


def _iso_to_unix(iso: str) -> int | None:
    if not iso:
        return None
    from datetime import datetime

    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def fetch() -> ProviderResult:
    try:
        proc = subprocess.run(
            ["gh", "api", "/copilot_internal/user"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        return ProviderResult(provider="copilot", error="gh CLI not installed")
    except subprocess.TimeoutExpired:
        return ProviderResult(provider="copilot", error="gh api timed out")

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).strip().splitlines()
        return ProviderResult(provider="copilot", error=msg[-1] if msg else "gh api failed")

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return ProviderResult(provider="copilot", error=f"invalid JSON: {e}")

    quotas = data.get("quota_snapshots") or {}
    reset_iso = data.get("quota_reset_date_utc") or data.get("quota_reset_date")
    resets_at = _iso_to_unix(reset_iso)

    windows: list[Window] = []
    for qid, label in (
        ("premium_interactions", "premium req"),
        ("chat", "chat"),
        ("completions", "completions"),
    ):
        q = quotas.get(qid)
        if not q:
            continue
        if q.get("unlimited"):
            windows.append(
                Window(label=label, used_percent=0.0, resets_at=resets_at, extra="unlimited")
            )
            continue
        remaining_pct = float(q.get("percent_remaining", 0))
        used_pct = max(0.0, 100.0 - remaining_pct)
        entitlement = q.get("entitlement") or 0
        remaining = q.get("remaining") or 0
        extra = f"{int(entitlement - remaining)}/{int(entitlement)}" if entitlement else ""
        windows.append(
            Window(label=label, used_percent=used_pct, resets_at=resets_at, extra=extra)
        )

    orgs = data.get("organization_list") or []
    org_label = orgs[0].get("login") if orgs else None
    plan = data.get("copilot_plan")

    return ProviderResult(
        provider="copilot",
        plan=plan,
        account=f"{data.get('login', '')}"
        + (f" ({org_label})" if org_label else ""),
        windows=windows,
    )
