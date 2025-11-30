## 1. Specify TTL cleanup behavior
- [x] 1.1 Add a requirement to `omniq-api-config` describing a public helper for TTL-based result cleanup.
- [x] 1.2 Clarify that the helper computes a cutoff timestamp from `result_ttl` and delegates to `BaseStorage.purge_results`.
- [x] 1.3 Document that v1 uses an explicit helper (no automatic background cleanup), leaving room for future schedulers.

## 2. Implement TTL cleanup helper
- [x] 2.1 Add an async helper on `AsyncOmniQ` (e.g., `purge_expired_results()`) that:
  - Computes `older_than = now - result_ttl` using the current settings
  - Calls `self.storage.purge_results(older_than)`
  - Returns the number of purged results.
- [x] 2.2 Add a sync wrapper method on `OmniQ` that forwards to the async helper.

## 3. Tests and validation
- [x] 3.1 Add tests that verify the helper uses `result_ttl` to compute the cutoff time and calls `purge_results` with the expected value.
- [x] 3.2 Add tests that verify only results older than the cutoff are removed.
- [x] 3.3 Add tests that verify the helper behaves sensibly when `result_ttl` is very small or large.

