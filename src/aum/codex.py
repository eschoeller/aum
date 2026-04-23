import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .model import ProviderResult, Window

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
                access = auth["tokens"]["account_id"]  # noqa: F841  (kept for parity)
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
    except Exception as e:  # noqa: BLE001
        return ProviderResult(provider="codex", error=f"{type(e).__name__}: {e}")


def _parse(data: dict) -> ProviderResult:
    rl = data.get("rate_limit") or {}
    windows = []

    primary = rl.get("primary_window")
    if primary:
        windows.append(
            Window(
                label="5h window",
                used_percent=float(primary.get("used_percent", 0)),
                resets_at=primary.get("reset_at"),
            )
        )

    secondary = rl.get("secondary_window")
    if secondary:
        windows.append(
            Window(
                label="7d window",
                used_percent=float(secondary.get("used_percent", 0)),
                resets_at=secondary.get("reset_at"),
            )
        )

    return ProviderResult(
        provider="codex",
        plan=data.get("plan_type"),
        account=data.get("email"),
        windows=windows,
    )
