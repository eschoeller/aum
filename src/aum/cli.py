import argparse
import concurrent.futures as cf
import json
import sys
import time
from dataclasses import asdict

from rich.console import Console
from rich.live import Live

from . import claude, codex, copilot, render
from .model import ProviderResult

PROVIDERS = {
    "claude": lambda args: claude.fetch(),
    "codex": lambda args: codex.fetch(auto_refresh=args.refresh),
    "copilot": lambda args: copilot.fetch(),
}


def _run(args) -> list[ProviderResult]:
    selected = args.provider or list(PROVIDERS.keys())
    with cf.ThreadPoolExecutor(max_workers=len(selected)) as ex:
        futures = {ex.submit(PROVIDERS[p], args): p for p in selected}
        results = [
            f.result() if not f.exception() else ProviderResult(provider=p, error=str(f.exception()))
            for f, p in futures.items()
        ]
    order = args.provider or list(PROVIDERS.keys())
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
        description="AI Usage Meter — unified plan quota view for Claude, Codex, Copilot",
    )
    p.add_argument(
        "-p",
        "--provider",
        action="append",
        choices=sorted(PROVIDERS.keys()),
        help="limit to one provider (repeatable); default: all",
    )
    p.add_argument(
        "--refresh",
        action="store_true",
        help="auto-refresh the Codex access token if expired (rewrites ~/.codex/auth.json)",
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
