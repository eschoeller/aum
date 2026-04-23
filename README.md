# aum

**AI Usage Meter** — unified plan-quota view for Claude Code, OpenAI Codex, and
GitHub Copilot. Shows real-time rolling-window usage percentages with progress
bars and reset timers.

```
┌ codex  plus  you@example.com ─────────────────────────────────────────────┐
│   5h window   █████░░░░░░░░░░░░░░░░░░░   21.0%  resets in 4h 58m          │
│   7d window   ██░░░░░░░░░░░░░░░░░░░░░░    9.4%  resets in 6d 23h          │
└───────────────────────────────────────────────────────────────────────────┘
┌ claude  max ──────────────────────────────────────────────────────────────┐
│   5h window   █████░░░░░░░░░░░░░░░░░░░   23.4%  resets in 2h 15m          │
│   7d window   ██░░░░░░░░░░░░░░░░░░░░░░   12.1%  resets in 4d  3h          │
└───────────────────────────────────────────────────────────────────────────┘
┌ copilot  business  your-org ──────────────────────────────────────────────┐
│   premium req █████░░░░░░░░░░░░░░░░░░░   23.4%  (70/300)  resets in 9d    │
│   chat        ░░░░░░░░░░░░░░░░░░░░░░░░    0.0%  (unlimited)               │
│   completions ░░░░░░░░░░░░░░░░░░░░░░░░    0.0%  (unlimited)               │
└───────────────────────────────────────────────────────────────────────────┘
```

## Where the data comes from

| Provider | Source | Freshness |
|---|---|---|
| **Claude Code** | `~/.claude/last_rate_limits.json` — written by the bundled statusline hook on every Claude Code turn (uses the `rate_limits` block Claude Code v1.2.80+ pipes to statusline scripts on stdin) | As of last Claude Code turn |
| **Codex** | `GET https://chatgpt.com/backend-api/wham/usage` with the access token from `~/.codex/auth.json` | Real-time |
| **Copilot** | `gh api /copilot_internal/user` — undocumented but stable internal endpoint, uses your existing `gh auth` token | Real-time |

None of these are approximations — all three are the same numbers the provider
UIs show.

## Install

Prerequisites: `python >= 3.10`, `pipx`, and `jq` (used by the Claude
statusline hook). On Debian/Ubuntu: `apt install pipx jq`.

```bash
git clone https://github.com/eschoeller/aum.git ~/projects/aum
pipx install ~/projects/aum            # or: pipx install -e ~/projects/aum for dev
```

Install the Claude statusline hook once (merges into existing settings):

```jsonc
// ~/.claude/settings.json
{
  "statusLine": {
    "type": "command",
    "command": "~/projects/aum/hooks/claude-statusline.sh"
  }
}
```

(Replace `~/projects/aum` with wherever you cloned the repo — Claude Code
expands `~` in the `command` field.)

## Usage

```bash
aum                    # show all three providers
aum -p codex           # one provider (repeatable)
aum --refresh          # auto-refresh Codex access token if expired
aum --json             # machine-readable
```

## Token refresh (Codex)

The Codex access token in `~/.codex/auth.json` lasts about an hour. Default
behavior on expiry: print a hint and exit non-zero for that provider. Passing
`--refresh` makes aum POST to `https://auth.openai.com/oauth/token` using the
refresh token and rewrite `auth.json` in place — matching what `codex` itself
does.

## Why not just use `ccusage` / `caut` / `claude-monitor`?

- **ccusage** parses local JSONL session logs and calculates token totals, but
  doesn't know your plan's 5h/7d caps — so it can't give you a percentage
  against the actual limit. Useful for cost/history views; not for "how close
  am I to being rate-limited."
- **caut** aggregates across providers but can't pull real quota on Linux
  without browser cookies — it falls back to CLI-based identity info only.
- **claude-monitor** approximates the plan cap from hardcoded token tables or
  ML detection over history. Close, but not authoritative.

aum asks each provider's own backend for the canonical number.
