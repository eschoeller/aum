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
jq -r '
  .rate_limits as $rl
  | if ($rl.five_hour // $rl.seven_day) then
      [
        (if $rl.five_hour then
          "5h \($rl.five_hour.used_percentage | floor)%"
         else empty end),
        (if $rl.seven_day then
          "7d \($rl.seven_day.used_percentage | floor)%"
         else empty end)
      ] | join(" · ")
    else
      empty
    end
' <<<"$input" | tr -d "\n"
