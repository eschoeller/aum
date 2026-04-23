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
#     "rate_limits": {
#       "five_hour":  {"used_percentage": 23.4, "resets_at": 1730000000},
#       "seven_day":  {"used_percentage": 12.1, "resets_at": 1730400000}
#     }
#   }
#
# Setting AUM_HOOK_DEBUG=1 writes every invocation's raw stdin to
# ~/.claude/aum-hook-debug.jsonl so you can see what Claude Code is passing.

set -uo pipefail

CACHE_DIR="${HOME}/.claude"
CACHE_FILE="${CACHE_DIR}/last_rate_limits.json"
DEBUG_FILE="${CACHE_DIR}/aum-hook-debug.jsonl"

input=$(cat)

# Optional raw-input trace for debugging what Claude Code is passing.
if [[ "${AUM_HOOK_DEBUG:-0}" == "1" ]]; then
  mkdir -p "$CACHE_DIR"
  printf '%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$input" >>"$DEBUG_FILE"
fi

# Bail silently if jq isn't installed or stdin is empty/whitespace. A missing
# hook should never block a Claude Code turn, and an empty invocation (e.g.
# a probe) must not clobber a previously-good cache.
if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi
if [[ -z "${input// /}" ]]; then
  exit 0
fi

# Reject non-JSON input early so we don't clobber the cache with nonsense.
if ! jq -e . >/dev/null 2>&1 <<<"$input"; then
  exit 0
fi

mkdir -p "$CACHE_DIR"

# Only refresh the cache if the input actually contains a rate_limits block.
# Otherwise leave the previous cached value alone — it may still be valid.
has_rl=$(jq -r '(.rate_limits // {}) | (.five_hour or .seven_day) | tostring' <<<"$input")
if [[ "$has_rl" == "true" ]]; then
  # Use `// null` (not `// empty`) for missing optional fields. `empty` in an
  # object construction aborts the whole object — so one missing field would
  # silently produce no cache output.
  new_cache=$(jq -c --arg captured "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
    {
      captured_at: $captured,
      plan:        (.plan // .subscription.plan // null),
      account:     (.account.email // .user.email // null),
      rate_limits: (.rate_limits // {})
    }
  ' <<<"$input")
  if [[ -n "$new_cache" ]]; then
    printf '%s' "$new_cache" >"${CACHE_FILE}.tmp"
    mv "${CACHE_FILE}.tmp" "$CACHE_FILE"
  fi
fi

# Statusline output — one line, no newline, so Claude renders it inline.
#
# Format: "5h: 23% (2h15m) · 7d: 12% (4d3h)"
#   - percentage is the used portion
#   - parenthesised value is time until reset
#   - "(now)" is shown if the reset timestamp has already passed
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
