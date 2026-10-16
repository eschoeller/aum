# Claude Usage KDE Plasma Widget — Local Fork

Forked from **Claude Usage 1.0.0** by [izll](https://github.com/anthropics/claude-usage-widget)
(original repo is no longer available). Licensed GPL-3.0-or-later.

## Changes from upstream 1.0.0

### 1.1.0 — Per-model (Fable) support

The upstream widget read per-model usage from `data.seven_day_sonnet` and
`data.seven_day_opus` — top-level fields in the API response that Anthropic
no longer populates. The API now returns a `limits` array with `weekly_scoped`
entries for per-model-family rate limits.

**API response parser** (`contents/ui/main.qml` → `fetchUsageFromApi`):
- Rewrote the parser to read the `limits` array first, falling back to the
  legacy top-level `five_hour`/`seven_day` keys for backwards compatibility.
- Each `limits` entry with `kind: "weekly_scoped"` is matched by
  `scope.model.display_name` (Fable, Sonnet, Opus).
- Reset times are also parsed from the `limits` array.

**Fable in taskbar** (compact representation):
- Added a third dot + percentage for Fable in the taskbar row, shown when
  `fableWeeklyPercent > 0`. Layout: `● 5% | ● 86% | ● 79%`

**Fable in popup** (full representation):
- Added a "Fable" row with a progress bar in the "By Model (Weekly)" section,
  above Sonnet and Opus.
- Updated the "no model data" fallback to account for Fable.

**Other changes:**
- Removed the Claude icon from the compact (taskbar) representation.
- Bumped version to 1.1.0 in `metadata.json`.

## Installation

```bash
# Copy to the Plasma widget directory
cp -r plasma-widget ~/.local/share/plasma/plasmoids/org.kde.plasma.claudeusage

# Restart plasmashell to pick up changes
kquitapp6 plasmashell && kstart plasmashell
```

Then right-click your panel → Add Widgets → search "Claude Usage".

## Configuration

Right-click the widget → Configure:
- **Refresh interval**: minutes between API polls (default 1; recommend 15
  to avoid 429 rate limits from `api.anthropic.com/api/oauth/usage`).
- **Language**: UI language for labels.
