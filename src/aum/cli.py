import argparse
import concurrent.futures as cf
import json
import sys
from dataclasses import asdict

from rich.console import Console

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
        return [
            f.result() if not f.exception() else ProviderResult(provider=p, error=str(f.exception()))
            for f, p in futures.items()
        ]


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
    args = p.parse_args()

    results = _run(args)
    # preserve the provider order the user passed (or default order)
    order = args.provider or list(PROVIDERS.keys())
    results.sort(key=lambda r: order.index(r.provider) if r.provider in order else 99)

    if args.json:
        payload = [asdict(r) for r in results]
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        render.render(results, console=Console())

    return 0 if not any(r.error for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
