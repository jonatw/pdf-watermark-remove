# Run Tests

Run the full test suite and analyze results.

---

## Steps

### 1. Unit Tests
```bash
python -m unittest tests.py -v
```

### 2. If all tests pass
- Report the number of tests passed
- Summarize test coverage areas (Config, exceptions, strategies, remover)

### 3. If any test fails
- List each failing test name and error message
- Read the relevant test code and the production code being tested
- Analyze root cause (production bug vs outdated test vs Config singleton leakage)
- Suggest fixes, but **do NOT modify test files automatically**

### 4. Build Verification (Docker)
```bash
docker build -t pdf-watermark-remover .
```

## Rules

- When tests fail, fix production code first — never modify tests without user approval
- Config uses singleton pattern — test isolation issues may be caused by state leakage, not bugs
