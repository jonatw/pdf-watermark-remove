# Code Review

Perform a full code review on current changes (`git diff main`).
Review based on this project's architecture and known risk areas.

---

## Architecture Context

- **Core logic**: `remove_watermark.py` orchestrates strategy selection; `strategies.py` implements XRef and text pattern removal
- **Strategy selection**: Producer metadata containing "Version" → XRef strategy; otherwise → CommonString strategy
- **Config singleton**: `Config()` is a singleton — changes persist across calls
- **Async pattern**: PyMuPDF is not thread-safe; async gather works cooperatively, not in parallel on the doc object
- **Server**: Flask with synchronous `asyncio.run()` per request

---

## 1. Watermark Strategy Logic

### XRef Strategy
- Are iPad screen resolution patterns correct (both portrait and landscape)?
- Is producer metadata check still matching "Version"?
- Is XRef deletion targeting the correct image?

### CommonString Strategy
- Is `MIN_PATTERN_LENGTH` (30) still appropriate for the target watermarks?
- Is `PATTERN_SEARCH_WINDOW` (300) sufficient?
- Does the `q...Q` block removal avoid removing legitimate content?
- Are all three operator types handled? (`(...)Tj`, `<...>Tj`, `[...]TJ`)

---

## 2. PDF Processing

- Is `fitz.Document` properly closed in all code paths (including errors)?
- Are file paths validated before processing?
- Is the Config singleton causing unintended side effects?
- Are async operations correctly awaited?

---

## 3. Server

- Is file upload validation working (PDF only, size limits)?
- Are temp files cleaned up on error paths?
- Is job state consistent under concurrent requests (thread lock usage)?
- XSS risk in templates with user-provided filenames?

---

## 4. Tests

- Do new features have corresponding test cases?
- Risk of breaking existing tests?
- Is Config singleton state leaking between test cases?

---

## Output Format

```
## Code Review Results

### FAIL — Must Fix
- [Description] (file:line)

### WARN — Suggested Improvements
- [Description] (file:line)

### PASS — Good Practices
- [Positive observations]

### Verdict
[Ready to merge / Needs changes / Do not merge] — reason
```
