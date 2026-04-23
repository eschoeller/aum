# aum

**AI Usage Meter** — unified plan-quota view for Claude Code, OpenAI Codex,
GitHub Copilot, and (opt-in) Google Gemini. Shows real-time rolling-window
usage percentages with progress bars and reset timers.

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
| **Claude Code** | `~/.claude/last_rate_limits.json` — written by the bundled statusline hook on every Claude Code turn (uses the `rate_limits` block Claude Code v1.2.80+ pipes to statusline scripts on stdin). Account and plan are resolved live from `~/.claude.json` and `~/.claude/.credentials.json`. | Windows: last Claude Code turn. Account/plan: real-time. |
| **Codex** | `GET https://chatgpt.com/backend-api/wham/usage` with the access token from `~/.codex/auth.json` | Real-time |
| **Copilot** | `gh api /copilot_internal/user` — undocumented but stable internal endpoint, uses your existing `gh auth` token | Real-time |
| **Gemini** (opt-in) | `POST cloudcode-pa.googleapis.com/v1internal:loadCodeAssist` → `:retrieveUserQuota` with the access token from `~/.gemini/oauth_creds.json` | Real-time |

None of these are approximations — all are the same numbers the provider UIs show.

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
aum                    # default set: claude, codex, copilot
aum -g                 # also fetch Gemini (opt-in; adds one HTTP dance)
aum -p codex           # one provider only; repeat to add more
aum -p claude -g       # claude + gemini (-g is additive with -p)
aum --no-refresh       # leave OAuth auth files untouched even if tokens expired
aum --json             # machine-readable
aum -w                 # live watch mode (redraws every second)
aum -w -n 30           # watch with 30-second refetch cadence
```

## Token refresh

Codex and Gemini both use short-lived OAuth access tokens (~1h). By default
aum auto-refreshes them when expired — it's what the upstream CLIs do on
startup, and avoids an ergonomic wall every hour.

- For **Codex**, POST the refresh token to `https://auth.openai.com/oauth/token`
  and rewrite `~/.codex/auth.json`.
- For **Gemini**, POST the refresh token to `https://oauth2.googleapis.com/token`
  (form-encoded per RFC 6749) and rewrite `~/.gemini/oauth_creds.json`.

Both operations preserve `0600` file permissions and use atomic
temp-file-plus-rename so concurrent aum processes don't corrupt auth state.

Pass `--no-refresh` if you'd rather aum never write to those files — aum will
then just surface a "token expired" error for that provider.

Copilot doesn't need refresh — `gh api` inherits whatever token `gh auth login`
stored in your keyring. Claude doesn't need refresh either — the statusline
hook just caches a local JSON snapshot.

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
