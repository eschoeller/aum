# AUM (AI Usage Meter) Code Review

**Project:** AI Usage Meter — unified plan-quota view for Claude Code, OpenAI Codex, and GitHub Copilot

**Repository:** `eschoeller/aum`

**Review Date:** 2026-04-23

---

## Executive Summary

This is **production-ready code** with excellent UX and thoughtful architecture. The main gaps are documentation and testing — adding these would make it significantly more maintainable. The codebase clearly prioritizes reliability (multiple error paths, token refresh logic, graceful degradation) which is appropriate for a monitoring tool.

**Code Stats:**
- **Total Lines:** ~900 (across 8 Python files + 1 bash hook)
- **Language:** Python 3.10+, Bash
- **Key Dependency:** `rich` (terminal UI rendering)
- **Architecture:** Modular, provider-based

---

## 📊 Code Quality Metrics

| Aspect | Rating | Notes |
|--------|--------|-------|
| Architecture | ⭐⭐⭐⭐⭐ | Clean separation, extensible |
| Error Handling | ⭐⭐⭐⭐☆ | Good but overly broad exceptions |
| Testing | ⭐⭐☆☆☆ | None visible |
| Documentation | ⭐⭐⭐☆☆ | Gemini excellent, others sparse |
| Security | ⭐⭐⭐⭐☆ | Token handling solid, could be more defensive |
| UX | ⭐⭐⭐⭐⭐ | Excellent terminal rendering |

---

## ✅ Strengths

### 1. Clean Architecture
- Each provider (claude, codex, copilot, gemini) has isolated modules
- Well-separated concerns: fetching, parsing, rendering
- Type hints used consistently throughout
- Easy to add new providers without touching existing code

### 2. Robust Error Handling
- Comprehensive error paths for network failures, missing auth files, expired tokens
- HTTP 401 handling with auto-refresh capability for Codex and Gemini
- Graceful fallbacks (e.g., Claude fetches locally-cached data from statusline hook)
- No crashes on edge cases; returns `ProviderResult` with error field instead

### 3. Smart Caching & Staleness
- Claude uses local cache populated by statusline hook (doesn't require API call)
- Staleness tracking with human-readable duration display (`render.py:69-70`)
- Token refresh logic with atomic file operations (temp file → move pattern prevents corruption)
- Proactive token expiry checks before API calls

### 4. Excellent UX Polish
- Progress bars with intelligent color coding (green → yellow at 75% → red at 90%)
- Live watch mode with independent render/refetch cycles
- Readable time formatting (e.g., "4d 3h" vs epoch timestamps)
- Machine-readable JSON output option
- Smooth statusline integration for Claude Code

### 5. Intelligent Provider Integration
- Clever plan label formatting (e.g., "max 5x" from `default_claude_max_5x`)
- Handles varying window types dynamically (Codex duration can differ by tier)
- Per-model quota tracking for Gemini
- Org detection for Copilot
- Detects and displays rate limit tiers accurately

---

## ⚠️ Areas for Improvement

### 1. Bare Exception Handling (Security/Maintainability)

**Files:** `codex.py:109`, `gemini.py:140`

```python
except Exception as e:  # noqa: BLE001
    return ProviderResult(provider="codex", error=f"{type(e).__name__}: {e}")
```

**Issue:** Using bare `except Exception` suppresses linter warnings with `noqa` comments, suggesting this was intentional but remains problematic. It's overly broad and can hide bugs.

**Recommendation:** Replace with specific error types:
```python
except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as e:
    return ProviderResult(provider="codex", error=f"{type(e).__name__}: {e}")
```

---

### 2. Thread Safety Documentation (Minor)

**File:** `cli.py:38-45`

```python
def _run(args) -> list[ProviderResult]:
    selected = _selected_providers(args)
    with cf.ThreadPoolExecutor(max_workers=len(selected)) as ex:
        futures = {ex.submit(PROVIDERS[p], args): p for p in selected}
        results = [...]
```

**Issue:** Results are fetched in parallel but rendered serially — the current code is thread-safe, but there's no explicit documentation of this pattern.

**Recommendation:** Add a comment explaining the threading model:
```python
# Fetching is parallelized; rendering is always serial.
# Each provider's fetch() is side-effect-free except for token refresh.
```

---

### 3. Hard-coded Magic Numbers (Maintainability)

**Files:** `render.py:8`, `copilot.py:24`, `cli.py:112`, `gemini.py:114`

```python
BAR_WIDTH = 24
timeout=15  # scattered across files
"interval must be at least 10 seconds"
expires_in * 1000  # converting to milliseconds
```

**Issue:** These are reasonable defaults but undocumented. A config file or constants module could help.

**Recommendation:** Create `src/aum/constants.py`:
```python
# API timeouts (seconds)
API_TIMEOUT = 15

# Terminal rendering
BAR_WIDTH = 24
COLOR_THRESHOLD_YELLOW = 75
COLOR_THRESHOLD_RED = 90

# CLI constraints
WATCH_INTERVAL_MIN = 10
WATCH_INTERVAL_DEFAULT = 60

# Token handling
GEMINI_EXPIRY_SCALE = 1000  # Convert seconds to milliseconds
```

---

### 4. File Permission Validation (Security)

**Files:** `codex.py:15-17`, `gemini.py:74-79`

```python
def _load_auth() -> dict:
    with AUTH_PATH.open() as f:
        return json.load(f)
```

**Issue:** Auth files are set to 0o600 during refresh (line 24, 78) but never validated at read time. If a user manually changes permissions or compromises occur, aum won't warn.

**Recommendation:** Add validation:
```python
def _validate_auth_permissions(path: Path) -> bool:
    """Ensure auth file has restrictive permissions."""
    stat = path.stat()
    # 0o600 in octal = 384 in decimal, but we check mode bits
    if stat.st_mode & 0o077:  # Check if group/other have any permissions
        raise PermissionError(f"{path} has overly permissive permissions")
    return True

def _load_auth() -> dict:
    _validate_auth_permissions(AUTH_PATH)
    with AUTH_PATH.open() as f:
        return json.load(f)
```

---

### 5. Fragile Token Expiry Check (Robustness)

**File:** `gemini.py:134-141`

```python
if auto_refresh and isinstance(creds.get("expiry_date"), int):
    if creds["expiry_date"] < int(time.time() * 1000):
```

**Issue:** Relies on `isinstance` check and assumes millisecond precision. If schema changes or a timestamp is stored as string, the check silently fails.

**Recommendation:** Add explicit validation:
```python
def _is_token_expired(creds: dict) -> bool:
    """Check if the stored token has expired."""
    expiry = creds.get("expiry_date")
    if not isinstance(expiry, int):
        return True  # Conservative: treat missing/invalid as expired
    return expiry < int(time.time() * 1000)
```

---

### 6. Dead Code (Maintenance)

**File:** `codex.py:95`

```python
access = auth["tokens"]["account_id"]  # noqa: F841  (kept for parity)
```

**Issue:** This variable is assigned but never used. The comment suggests it was kept intentionally for "parity," but it creates maintenance confusion.

**Recommendation:** Remove the assignment:
```python
# Removed unused line; using account_id directly below
data = _fetch_usage(
    auth["tokens"]["access_token"],
    auth["tokens"]["account_id"],
)
```

---

### 7. Missing Test Suite (Reliability)

**Issue:** No visible tests for:
- Parsing logic from each provider's response format
- Window generation and ordering
- Token refresh flows
- Error handling paths
- Watch mode timing

**Recommendation:** Add `tests/` directory with:
- `test_claude.py` — mock Claude response parsing
- `test_codex.py` — mock Codex API responses (test both fresh and expired tokens)
- `test_copilot.py` — mock Copilot quota snapshot structure
- `test_gemini.py` — mock per-model quota returns
- `test_render.py` — ensure progress bars render correctly at edge percentages (0%, 99.9%, 100%)

Example test:
```python
def test_color_threshold_90_percent():
    """Bar should be red at 90% and above."""
    from aum.render import _bar_color
    assert _bar_color(89.9) == "yellow"
    assert _bar_color(90.0) == "red"
    assert _bar_color(100.0) == "red"
```

---

### 8. Sparse Documentation (Maintainability)

**Issue:** Most modules lack docstrings explaining contracts. `gemini.py` has excellent module docstring (lines 1-18), but others don't.

**Recommendation:** Add docstrings to all provider modules:

```python
"""Claude rate-limit fetcher.

Reads from ~/.claude/last_rate_limits.json, which is populated by the
Claude Code statusline hook (see hooks/claude-statusline.sh).

Returns the same rate limit data that Claude Code's UI shows, plus
staleness info if the cache is old (e.g., from a previous session).

Note: This fetcher does NOT make network calls; it only reads local cache.
"""
```

---

## 🔒 Security Assessment

### Strengths
- ✅ Tokens stored with 0o600 permissions during refresh
- ✅ OAuth tokens not logged or printed in errors
- ✅ Atomic file writes prevent partial/corrupted state
- ✅ Refresh token rotation handled (Gemini, Codex)

### Gaps
- ⚠️ No validation that auth files remain restrictive at read time
- ⚠️ Error messages might leak hostname/path info in some edge cases
- ⚠️ No rate-limit backoff (could hammer API on repeated errors)

---

## 🧪 Testing Recommendations

### Priority 1: Parser Tests
```python
# Test the critical parsing paths — these are most likely to break on API changes
def test_claude_window_parsing():
    """Ensure claude.py extracts windows correctly from cache."""
    cache = {
        "five_hour": {"used_percentage": 23.4, "resets_at": 1730000000},
        "seven_day": {"used_percentage": 12.1, "resets_at": 1730400000},
    }
    # verify Window creation...

def test_codex_plan_formatting():
    """Verify plan label generation matches provider responses."""
    # Test "max 5x", "plus", etc.
```

### Priority 2: Integration Tests
- Mock network calls; verify fetch() returns correct ProviderResult shapes
- Test token refresh flows (simulate 401 → refresh → retry)
- Test watch mode refetch timing

### Priority 3: Regression Tests
- Ensure renders match expected format (progress bars, colors, durations)
- Test edge cases (0% used, 100% used, negative resets_at)

---

## 📋 Specific Action Items

### High Priority (Correctness/Security)
- [ ] Add file permission validation for auth files (`codex.py`, `gemini.py`)
- [ ] Remove dead code assignment at `codex.py:95`
- [ ] Replace bare `except Exception` with specific error types

### Medium Priority (Maintainability)
- [ ] Create `src/aum/constants.py` for magic numbers
- [ ] Add module docstrings to `claude.py`, `codex.py`, `copilot.py`
- [ ] Add inline comments explaining threading model in `cli.py`
- [ ] Improve token expiry validation in `gemini.py`

### Low Priority (Enhancement)
- [ ] Add unit tests (parser tests, render tests)
- [ ] Add integration tests for token refresh
- [ ] Document API response schemas in module docstrings
- [ ] Add rate-limit backoff strategy

---

## 🎯 Conclusion

**What's Working Well:**
- Clean, modular architecture makes it easy to add providers
- Excellent error handling and graceful degradation
- Outstanding terminal UX with progress bars and live watch mode
- Smart token refresh with atomic file operations

**What Needs Attention:**
- Add comprehensive tests (parser + integration)
- Tighten exception handling (specific error types)
- Add security hardening (file permission validation)
- Improve documentation (docstrings, constants)

**Overall:** This is a solid, production-ready tool that prioritizes reliability and UX. With the recommended improvements, it would be excellent for enterprise use and contribution.

---

## Appendix: File Structure

```
src/aum/
├── __init__.py           # Version only
├── cli.py               # CLI entry point, provider orchestration
├── model.py             # Dataclasses (ProviderResult, Window)
├── render.py            # Terminal rendering, progress bars
├── claude.py            # Claude rate limit fetcher (local cache)
├── codex.py             # OpenAI Codex fetcher (HTTP + token refresh)
├── copilot.py           # GitHub Copilot fetcher (gh CLI)
└── gemini.py            # Google Gemini fetcher (HTTP + token refresh)

hooks/
└── claude-statusline.sh  # Statusline hook for Claude Code (bash)

pyproject.toml           # Package config, depends on 'rich'
README.md               # Installation, usage docs
```

---

**Review prepared by:** GitHub Copilot CLI  
**Session ID:** d7055339-cb8b-4e9f-b625-5779e786cbf8
