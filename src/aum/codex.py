"""OpenAI Codex CLI plan-quota fetcher.

Hits ``chatgpt.com/backend-api/wham/usage`` — the same undocumented
internal endpoint Codex CLI's ``/status`` command uses — authenticated
with the access token Codex stashes in ``~/.codex/auth.json`` during
``codex login``. Returns the two rolling windows OpenAI reports
(``primary_window`` and ``secondary_window``, currently 5h / 7d on the
Plus plan) with labels derived from ``limit_window_seconds`` so a
future plan with different durations renders correctly.

If the access token is expired (~1h lifetime), ``fetch(auto_refresh=True)``
will POST the refresh token to ``https://auth.openai.com/oauth/token``
and rewrite ``auth.json`` in place — matching what ``codex`` itself does.
Without ``auto_refresh``, a 401 is surfaced as a user-facing error.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .model import ProviderResult, Window

# Broad-but-named tuple covering anything these HTTP + file-backed code
# paths can raise. Preferred over `except Exception` so genuinely
# unexpected bugs (e.g. programming errors) still surface as tracebacks.
_EXPECTED_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    OSError,
    json.JSONDecodeError,
    KeyError,
    RuntimeError,
)

AUTH_PATH = Path.home() / ".codex" / "auth.json"
USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
TOKEN_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"


def _load_auth() -> dict:
    with AUTH_PATH.open() as f:
        return json.load(f)


def _save_auth(data: dict) -> None:
    tmp = AUTH_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, 0o600)
    tmp.replace(AUTH_PATH)


def _refresh_access_token(auth: dict) -> dict:
    refresh_token = auth.get("tokens", {}).get("refresh_token")
    if not refresh_token:
        raise RuntimeError("no refresh_token in ~/.codex/auth.json")

    body = json.dumps(
        {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode()

    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())

    tokens = auth.setdefault("tokens", {})
    tokens["access_token"] = payload["access_token"]
    tokens["id_token"] = payload.get("id_token", tokens.get("id_token"))
    if payload.get("refresh_token"):
        tokens["refresh_token"] = payload["refresh_token"]
    from datetime import datetime, timezone

    auth["last_refresh"] = datetime.now(timezone.utc).isoformat()
    return auth


def _fetch_usage(access_token: str, account_id: str) -> dict:
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "ChatGPT-Account-Id": account_id,
            "User-Agent": "codex-cli",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch(*, auto_refresh: bool = False) -> ProviderResult:
    if not AUTH_PATH.exists():
        return ProviderResult(provider="codex", error=f"{AUTH_PATH} not found")

    try:
        auth = _load_auth()
        tokens = auth.get("tokens", {}) or {}
        access = tokens.get("access_token")
        account = tokens.get("account_id")
        if not access or not account:
            return ProviderResult(
                provider="codex",
                error="access_token or account_id missing from auth.json",
            )

        try:
            data = _fetch_usage(access, account)
        except urllib.error.HTTPError as e:
            if e.code == 401 and auto_refresh:
                auth = _refresh_access_token(auth)
                _save_auth(auth)
                data = _fetch_usage(
                    auth["tokens"]["access_token"],
                    auth["tokens"]["account_id"],
                )
            elif e.code == 401:
                return ProviderResult(
                    provider="codex",
                    error="access token expired — run `codex` once, or pass --refresh",
                )
            else:
                return ProviderResult(provider="codex", error=f"HTTP {e.code}: {e.reason}")

        return _parse(data)
    except _EXPECTED_ERRORS as e:
        return ProviderResult(provider="codex", error=f"{type(e).__name__}: {e}")


def _window_label(seconds: int | None, fallback: str) -> str:
    """Derive a human label from the window duration the API reports.
    `limit_window_seconds` is the source of truth — don't assume Plus's
    5h/7d are universal."""
    if not seconds:
        return fallback
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d window"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h window"
    if seconds % 60 == 0:
        return f"{seconds // 60}m window"
    return f"{seconds}s window"


def _parse(data: dict) -> ProviderResult:
    rl = data.get("rate_limit") or {}
    windows = []

    for key, fallback in (("primary_window", "primary"), ("secondary_window", "secondary")):
        block = rl.get(key)
        if not block:
            continue
        windows.append(
            Window(
                label=_window_label(block.get("limit_window_seconds"), fallback),
                used_percent=float(block.get("used_percent", 0)),
                resets_at=block.get("reset_at"),
            )
        )

    return ProviderResult(
        provider="codex",
        plan=data.get("plan_type"),
        account=data.get("email"),
        windows=windows,
    )
