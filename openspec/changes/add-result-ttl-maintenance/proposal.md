## Why
The v1 PRD and `Settings` model introduce a `result_ttl` / `OMNIQ_RESULT_TTL` configuration, and storage backends expose `purge_results(older_than)` for cleanup. However, there is no explicit specification or high-level behavior tying these together, and no documented way for users to trigger TTL-based cleanup through the public API.

This makes result TTL effectively a dead configuration knob and leaves cleanup strategy underspecified for v1 users.

## What Changes
- Define how `result_ttl` in settings is used to compute a cutoff time for result cleanup.
- Specify a small high-level API surface (async and sync) that triggers TTL-based cleanup using `BaseStorage.purge_results`.
- Clarify expectations around when and how often cleanup is invoked (on-demand helper vs internal background job, with v1 favoring explicit on-demand calls).

## Impact
- Makes the existing `result_ttl` configuration meaningful and discoverable.
- Provides a simple, explicit mechanism for applications to clean up old results without introducing additional worker types or schedulers.
- Keeps v1 behavior minimal and opt-in, while leaving room for more advanced cleanup strategies later.

