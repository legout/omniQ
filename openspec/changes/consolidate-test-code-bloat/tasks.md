## 1. Convert scripts to pytest suite
**Priority**: HIGH

- [ ] Add `pytest` to dev dependencies (if not already present)
- [ ] Create `tests/` structure and `tests/conftest.py`
- [ ] Move root-level `test_*.py` scripts into `tests/` and convert to pytest style
- [ ] Remove `sys.path` manipulation and standardize imports (use `omniq.*`)

## 2. Make async tests deterministic
**Priority**: HIGH

- [ ] Replace `time.sleep()` usage in async flows with coordination primitives and timeouts
- [ ] Add small helper(s) for “wait until condition” with a bounded timeout
- [ ] Avoid reliance on real-time delays for retry/interval tests where possible

## 3. Reduce duplication via fixtures/helpers
**Priority**: MEDIUM

- [ ] Add fixtures for temp dirs, settings, storage creation, and queue/worker setup
- [ ] Parameterize backends/serializers only where it reduces duplication (avoid cross-product explosion)

## 4. Validation
**Priority**: MEDIUM

- [ ] Run the pytest suite locally and ensure it is stable (no flaky timing)
- [ ] Document how to run tests in `README.md` or `docs/` (short section)
