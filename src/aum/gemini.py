"""Gemini CLI (Code Assist) plan-quota fetcher.

The Gemini free tier (``Code Assist for individuals``) uses an undocumented
internal endpoint at ``cloudcode-pa.googleapis.com/v1internal`` — the same
one Gemini CLI's ``/stats`` command hits. Quota is reported per-model as a
``remainingFraction`` (0..1) with a daily ``resetTime``.

Two-step dance:

1. ``POST :loadCodeAssist`` — returns the ``cloudaicompanionProject`` id
   (not persisted locally by Gemini CLI).
2. ``POST :retrieveUserQuota`` with that project id — returns per-model
   buckets.

Unlike Codex/Copilot, Gemini is opt-in in aum (``-p gemini`` or ``--gemini``)
because the orchestration is noisier and most people on the free tier don't
hit the cap.
"""

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .model import ProviderResult, Window

CREDS_PATH = Path.home() / ".gemini" / "oauth_creds.json"
ACCOUNTS_PATH = Path.home() / ".gemini" / "google_accounts.json"
BASE_URL = "https://cloudcode-pa.googleapis.com/v1internal"
# Epoch-zero resetTime signals "not available on this tier" (e.g. Pro models
# on the free tier). Drop those rather than rendering them as 100% used.
NOT_AVAILABLE_RESET = "1970-01-01T00:00:00Z"


def _post(url: str, body: dict, access_token: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _iso_to_unix(iso: str) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _load_account() -> str | None:
    try:
        return json.loads(ACCOUNTS_PATH.read_text()).get("active")
    except (OSError, json.JSONDecodeError):
        return None


def fetch() -> ProviderResult:
    if not CREDS_PATH.exists():
        return ProviderResult(provider="gemini", error=f"{CREDS_PATH} not found")

    try:
        creds = json.loads(CREDS_PATH.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return ProviderResult(provider="gemini", error=f"creds unreadable: {e}")

    access = creds.get("access_token")
    if not access:
        return ProviderResult(provider="gemini", error="no access_token in oauth_creds.json")

    try:
        load = _post(f"{BASE_URL}:loadCodeAssist", {"metadata": {"pluginType": "GEMINI"}}, access)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return ProviderResult(
                provider="gemini",
                error="access token expired — run `gemini` once to refresh",
            )
        return ProviderResult(provider="gemini", error=f"loadCodeAssist HTTP {e.code}: {e.reason}")
    except (urllib.error.URLError, TimeoutError) as e:
        return ProviderResult(provider="gemini", error=f"loadCodeAssist: {e}")

    project = load.get("cloudaicompanionProject")
    tier = (load.get("currentTier") or {}).get("name") or (load.get("currentTier") or {}).get("id")
    if not project:
        return ProviderResult(
            provider="gemini",
            plan=tier,
            account=_load_account(),
            error="no cloudaicompanionProject returned by loadCodeAssist",
        )

    try:
        quota = _post(f"{BASE_URL}:retrieveUserQuota", {"project": project}, access)
    except urllib.error.HTTPError as e:
        return ProviderResult(
            provider="gemini",
            plan=tier,
            account=_load_account(),
            error=f"retrieveUserQuota HTTP {e.code}: {e.reason}",
        )

    windows: list[Window] = []
    for bucket in quota.get("buckets") or []:
        if bucket.get("resetTime") == NOT_AVAILABLE_RESET:
            continue
        fraction = bucket.get("remainingFraction")
        if fraction is None:
            continue
        used_pct = max(0.0, min(100.0, (1 - float(fraction)) * 100))
        model_id = bucket.get("modelId") or "?"
        # Strip redundant "gemini-" prefix; the panel header already names
        # the provider. "gemini-2.5-flash" -> "2.5-flash"
        label = model_id[len("gemini-") :] if model_id.startswith("gemini-") else model_id
        windows.append(
            Window(
                label=label,
                used_percent=used_pct,
                resets_at=_iso_to_unix(bucket.get("resetTime")),
            )
        )

    return ProviderResult(
        provider="gemini",
        plan=tier,
        account=_load_account(),
        windows=windows,
    )
