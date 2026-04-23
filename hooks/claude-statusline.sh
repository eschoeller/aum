#!/usr/bin/env bash
#
# Claude Code statusline hook for aum.
#
# Reads session JSON on stdin, extracts the rate_limits block (Claude Code
# v1.2.80+) and its surrounding metadata, caches the result to
# ~/.claude/last_rate_limits.json, and prints a terse single-line summary
# that Claude Code displays as the statusline.
#
# Expected stdin shape (abridged):
#   {
#     "model": {"display_name": "..."},
#     "plan": "max",
#     "workspace": {...},
#     "rate_limits": {
#       "five_hour":  {"used_percentage": 23.4, "resets_at": 1730000000},
#       "seven_day":  {"used_percentage": 12.1, "resets_at": 1730400000}
#     }
#   }

set -euo pipefail

CACHE_DIR="${HOME}/.claude"
CACHE_FILE="${CACHE_DIR}/last_rate_limits.json"

input=$(cat)

# Bail out silently if jq isn't available — a missing hook should never block
# a Claude Code turn.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

mkdir -p "$CACHE_DIR"

# Cache rate_limits plus any plan/account metadata the session JSON exposes.
# `// empty` means "omit the key" so we don't write nulls into the cache.
jq -c --arg captured "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
  {
    captured_at: $captured,
    plan:        (.plan // .subscription.plan // empty),
    account:     (.account.email // .user.email // empty),
    rate_limits: (.rate_limits // {})
  }
' <<<"$input" >"${CACHE_FILE}.tmp"
mv "${CACHE_FILE}.tmp" "$CACHE_FILE"

# Statusline output — one line, no newline, so Claude renders it inline.
#
# Format: "5h: 23% (2h15m) · 7d: 12% (4d3h)"
#   - percentage is the used portion
#   - parenthesised value is time until reset
#   - "(now)" is shown if the reset timestamp has already passed (stale)
jq -r '
  def fmt_delta(s):
    if s <= 0 then "now"
    elif s >= 86400 then "\(s/86400 | floor)d\((s%86400)/3600 | floor)h"
    elif s >= 3600  then "\(s/3600  | floor)h\((s%3600) /60   | floor)m"
    else                  "\(s/60    | floor)m"
    end;

  def fmt_window(tag; w):
    if w == null then empty
    else
      "\(tag): \(w.used_percentage | floor)%"
      + (if w.resets_at then " (\(fmt_delta(w.resets_at - now)))" else "" end)
    end;

  .rate_limits as $rl
  | [fmt_window("5h"; $rl.five_hour), fmt_window("7d"; $rl.seven_day)]
  | map(select(. != null))
  | join(" · ")
' <<<"$input" | tr -d "\n"
