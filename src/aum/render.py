import time

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

BAR_WIDTH = 24

from .model import ProviderResult, Window


def _fmt_duration(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def _fmt_reset(resets_at: int | None) -> str:
    if not resets_at:
        return ""
    delta = resets_at - int(time.time())
    if delta < 0:
        return "resets now"
    return f"resets in {_fmt_duration(delta)}"


def _bar_color(pct: float) -> str:
    if pct >= 90:
        return "red"
    if pct >= 75:
        return "yellow"
    return "green"


def _make_bar(pct: float) -> Text:
    filled = round(pct / 100 * BAR_WIDTH)
    filled = max(0, min(BAR_WIDTH, filled))
    bar = Text()
    bar.append("█" * filled, style=_bar_color(pct))
    bar.append("░" * (BAR_WIDTH - filled), style="grey30")
    return bar


def _window_row(w: Window, table: Table) -> None:
    pct = max(0.0, min(100.0, w.used_percent))
    right_bits = [f"{pct:5.1f}%"]
    if w.extra:
        right_bits.append(f"({w.extra})")
    reset_str = _fmt_reset(w.resets_at)
    if reset_str:
        right_bits.append(reset_str)
    table.add_row(Text(w.label, style="dim"), _make_bar(pct), Text("  ".join(right_bits)))


def _header(r: ProviderResult) -> Text:
    parts: list[tuple[str, str]] = [(r.provider, "bold")]
    if r.plan:
        parts.append((f"  {r.plan}", "cyan"))
    if r.account:
        parts.append((f"  {r.account}", "dim"))
    if r.stale_seconds is not None and r.stale_seconds > 60:
        parts.append((f"  (stale: {_fmt_duration(r.stale_seconds)} old)", "yellow"))
    text = Text()
    for s, style in parts:
        text.append(s, style=style)
    return text


def _panel(r: ProviderResult) -> Panel:
    if r.error:
        body = Text(r.error, style="red")
    elif not r.windows:
        body = Text("no windows reported", style="dim")
    else:
        # Label column auto-sizes to the widest label in this panel so
        # longer labels (e.g. Gemini's per-model rows) render cleanly.
        label_width = max((len(w.label) for w in r.windows), default=11)
        table = Table.grid(padding=(0, 2))
        table.add_column(width=label_width)
        table.add_column(width=BAR_WIDTH)
        table.add_column()
        for w in r.windows:
            _window_row(w, table)
        body = table
    return Panel(body, title=_header(r), title_align="left", border_style="dim")


def build(results: list[ProviderResult]) -> Group:
    """Build the renderable for a snapshot. Reused for both one-shot and watch."""
    return Group(*(_panel(r) for r in results))


def render(results: list[ProviderResult], console: Console | None = None) -> None:
    c = console or Console()
    c.print(build(results))
