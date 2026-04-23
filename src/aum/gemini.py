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
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from .model import ProviderResult, Window

CREDS_PATH = Path.home() / ".gemini" / "oauth_creds.json"
ACCOUNTS_PATH = Path.home() / ".gemini" / "google_accounts.json"
BASE_URL = "https://cloudcode-pa.googleapis.com/v1internal"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# These are taken verbatim from Gemini CLI's code_assist/oauth2.ts — the
# upstream comment notes that for "installed applications" Google does not
# treat the client secret as confidential, so embedding is expected.
OAUTH_CLIENT_ID = "681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
OAUTH_CLIENT_SECRET = "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"
# Epoch-zero resetTime signals "not available on this tier" (e.g. Pro models
# on the free tier). Drop those rather than rendering them as 100% used.
NOT_AVAILABLE_RESET = "1970-01-01T00:00:00Z"

# Narrow tuple covering anything the refresh + save code paths can raise.
_REFRESH_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    OSError,
    json.JSONDecodeError,
    KeyError,
    RuntimeError,
)


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


def _is_token_expired(creds: dict) -> bool:
    """Return True if the cached access token is past its expiry.

    Gemini CLI stores ``expiry_date`` as a unix timestamp in milliseconds
    (not seconds). Missing or non-integer values are conservatively treated
    as expired so a refresh gets attempted.
    """
    expiry = creds.get("expiry_date")
    if not isinstance(expiry, int):
        return True
    return expiry < int(time.time() * 1000)


def _save_creds(creds: dict) -> None:
    tmp = CREDS_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(creds, f, indent=2)
    os.chmod(tmp, 0o600)
    tmp.replace(CREDS_PATH)


def _refresh_access_token(creds: dict) -> dict:
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("no refresh_token in oauth_creds.json")

    # Google's token endpoint documents application/x-www-form-urlencoded for
    # the refresh_token grant; JSON happens to work but isn't the documented
    # contract. Use form-encoded per RFC 6749 §3.2 and Google's docs.
    body = urllib.parse.urlencode(
        {
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())

    creds["access_token"] = payload["access_token"]
    creds["token_type"] = payload.get("token_type", creds.get("token_type", "Bearer"))
    if "id_token" in payload:
        creds["id_token"] = payload["id_token"]
    if "scope" in payload:
        creds["scope"] = payload["scope"]
    if "refresh_token" in payload:
        # Google sometimes rotates the refresh token; keep the new one.
        creds["refresh_token"] = payload["refresh_token"]
    # Gemini CLI stores expiry_date as unix millis, not seconds.
    expires_in = int(payload.get("expires_in", 3599))
    creds["expiry_date"] = int(time.time() * 1000) + expires_in * 1000
    return creds


def fetch(*, auto_refresh: bool = False) -> ProviderResult:
    if not CREDS_PATH.exists():
        return ProviderResult(provider="gemini", error=f"{CREDS_PATH} not found")

    try:
        creds = json.loads(CREDS_PATH.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return ProviderResult(provider="gemini", error=f"creds unreadable: {e}")

    access = creds.get("access_token")
    if not access:
        return ProviderResult(provider="gemini", error="no access_token in oauth_creds.json")

    # Proactively refresh if the stored expiry is in the past and the caller
    # opted in — saves a round trip vs. waiting for the 401.
    if auto_refresh and _is_token_expired(creds):
        try:
            creds = _refresh_access_token(creds)
            _save_creds(creds)
            access = creds["access_token"]
        except _REFRESH_ERRORS as e:
            return ProviderResult(provider="gemini", error=f"token refresh failed: {e}")

    try:
        load = _post(f"{BASE_URL}:loadCodeAssist", {"metadata": {"pluginType": "GEMINI"}}, access)
    except urllib.error.HTTPError as e:
        if e.code == 401 and auto_refresh:
            try:
                creds = _refresh_access_token(creds)
                _save_creds(creds)
                access = creds["access_token"]
                load = _post(
                    f"{BASE_URL}:loadCodeAssist",
                    {"metadata": {"pluginType": "GEMINI"}},
                    access,
                )
            except _REFRESH_ERRORS as e2:
                return ProviderResult(provider="gemini", error=f"token refresh failed: {e2}")
        elif e.code == 401:
            return ProviderResult(
                provider="gemini",
                error="access token expired — run `gemini` once, or pass --refresh",
            )
        else:
            return ProviderResult(
                provider="gemini", error=f"loadCodeAssist HTTP {e.code}: {e.reason}"
            )
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
