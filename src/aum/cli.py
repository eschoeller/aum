import argparse
import concurrent.futures as cf
import json
import sys
import time
from dataclasses import asdict

from rich.console import Console
from rich.live import Live

from . import claude, codex, copilot, gemini, render
from .model import ProviderResult

PROVIDERS = {
    "claude": lambda args: claude.fetch(),
    "codex": lambda args: codex.fetch(auto_refresh=args.refresh),
    "copilot": lambda args: copilot.fetch(),
    "gemini": lambda args: gemini.fetch(auto_refresh=args.refresh),
}

# Gemini is opt-in because its two-step orchestration (loadCodeAssist +
# retrieveUserQuota) is slower than the other providers, and most free-tier
# users don't hit the cap. Enabled via -p gemini or --gemini.
DEFAULT_PROVIDERS = ["claude", "codex", "copilot"]


def _selected_providers(args) -> list[str]:
    # -p sets the base selection (default set otherwise); --gemini is additive
    # in both cases, so `aum -p claude --gemini` fetches claude + gemini.
    # dict.fromkeys preserves order while collapsing repeats, so
    # `aum -p codex -p codex` fetches codex once.
    if args.provider:
        selected = list(dict.fromkeys(args.provider))
    else:
        selected = list(DEFAULT_PROVIDERS)
    if args.gemini and "gemini" not in selected:
        selected.append("gemini")
    return selected


def _run(args) -> list[ProviderResult]:
    # Provider fetches run in parallel; rendering is serial. Each fetch is
    # self-contained — it only touches its own ~/.<provider>/* files, so
    # running them concurrently is safe. Token-refresh writes go through
    # atomic temp-file-plus-rename, which also tolerates two aum processes
    # racing on the same account.
    selected = _selected_providers(args)
    with cf.ThreadPoolExecutor(max_workers=len(selected)) as ex:
        futures = {ex.submit(PROVIDERS[p], args): p for p in selected}
        results: list[ProviderResult] = []
        for f, p in futures.items():
            exc = f.exception()
            if exc is None:
                results.append(f.result())
            else:
                # Include the exception class name so generic messages like
                # KeyError: 'access_token' render as 'KeyError: access_token'
                # rather than bare "'access_token'".
                results.append(
                    ProviderResult(provider=p, error=f"{type(exc).__name__}: {exc}")
                )
    order = _selected_providers(args)
    results.sort(key=lambda r: order.index(r.provider) if r.provider in order else 99)
    return results


def _watch_loop(args, console: Console) -> int:
    # Redraw every second so reset countdowns tick smoothly; only refetch from
    # the network every --interval seconds to avoid hammering provider APIs.
    results = _run(args)
    last_fetch = time.monotonic()

    with Live(render.build(results), console=console, refresh_per_second=1, screen=False) as live:
        try:
            while True:
                time.sleep(1)
                if time.monotonic() - last_fetch >= args.interval:
                    results = _run(args)
                    last_fetch = time.monotonic()
                live.update(render.build(results))
        except KeyboardInterrupt:
            return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="aum",
        description=(
            "AI Usage Meter — unified plan quota view for Claude Code, "
            "OpenAI Codex, GitHub Copilot, and (opt-in) Google Gemini"
        ),
    )
    p.add_argument(
        "-p",
        "--provider",
        action="append",
        choices=sorted(PROVIDERS.keys()),
        help="limit to one provider (repeatable); default: all",
    )
    # Default is to refresh — this matches what codex/gemini themselves do at
    # startup, and aum's token writes are atomic (temp + rename, 0600). Pass
    # --no-refresh if you'd rather leave the auth files untouched and see a
    # "token expired" error instead.
    p.add_argument(
        "--no-refresh",
        dest="refresh",
        action="store_false",
        default=True,
        help=(
            "don't auto-refresh expired OAuth tokens for Codex "
            "(~/.codex/auth.json) or Gemini (~/.gemini/oauth_creds.json)"
        ),
    )
    p.add_argument(
        "-g",
        "--gemini",
        action="store_true",
        help="also fetch Gemini (opt-in; extra HTTP round-trip to cloudcode-pa)",
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of rendered panels")
    p.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="live-refresh mode — redraws every second, refetches every --interval seconds",
    )
    p.add_argument(
        "-n",
        "--interval",
        type=int,
        default=60,
        metavar="SECONDS",
        help="seconds between network refetches in --watch mode (default: 60)",
    )
    args = p.parse_args()

    if args.watch and args.json:
        p.error("--watch and --json are mutually exclusive")
    if args.interval < 10 and args.watch:
        p.error("--interval must be at least 10 seconds")

    console = Console()

    if args.watch:
        return _watch_loop(args, console)

    results = _run(args)

    if args.json:
        payload = [asdict(r) for r in results]
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        render.render(results, console=console)

    return 0 if not any(r.error for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
