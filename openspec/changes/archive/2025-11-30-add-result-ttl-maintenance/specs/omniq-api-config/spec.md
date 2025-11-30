## ADDED Requirements

### Requirement: Result TTL cleanup helper
The high-level API MUST provide a helper to clean up old task results based on the configured result TTL.

#### Scenario: Cleanup old results using settings
- **GIVEN** a `Settings` instance with `result_ttl` set to a positive number of seconds
- **AND** an `AsyncOmniQ` (or sync `OmniQ`) instance using storage that contains results both older and newer than `now - result_ttl`
- **WHEN** the caller invokes a TTL cleanup helper (for example, `purge_expired_results()` on the OmniQ interface)
- **THEN** the helper MUST compute a cutoff time as the current time minus `result_ttl`
- **AND** MUST call `BaseStorage.purge_results(cutoff)` on the underlying storage
- **AND** MUST return the number of results purged as reported by the storage backend
- **AND** MUST leave newer results (with completion times at or after the cutoff) intact.

