# Change: Remove duplicate `docs/examples` directory

## Why
The `docs/examples/` directory contains duplicate content that mirrors the root `examples/` directory. This creates several issues:

- **Unnecessary duplication**: Same example files exist in both locations (verified by file size comparison)
- **Violates conventions**: Python projects typically keep examples in root directory, not in docs/
- **Confusing structure**: Two example directories create ambiguity about which is canonical
- **Wasted maintenance**: Changes to examples must be mirrored in two places

The root `examples/` directory is the canonical location:
- Already referenced by all documentation (README.md, tutorials, how-to guides)
- Has more content (includes `basic_retry_example.py` not in docs/examples/)
- Follows Python project conventions
- No references to `docs/examples/` in mkdocs.yml or other config

## What Changes
Remove `docs/examples/` directory entirely (7 files).

### Files to Remove
```
docs/examples/
├── README.md
├── 01_quickstart_async.py
├── 02_scheduling_eta_and_interval.py
├── 03_retries_and_task_errors.py
├── 04_sync_api_logging_and_env.py
├── basic_retry_example.py
└── tasks.py
```

### Files to Keep
```
examples/ (root level)
├── README.md
├── 01_quickstart_async.py
├── 02_scheduling_eta_and_interval.py
├── 03_retries_and_task_errors.py
├── 04_sync_api_logging_and_env.py
├── basic_retry_example.py
└── tasks.py
```

## Impact
- **Affected code**: None (documentation-only change)
- **Affected docs**: None (docs already reference `examples/` not `docs/examples/`)
- **Breaking changes**: None (no external links to `docs/examples/`)
- **Risk**: Zero (canonical location already used everywhere)

## Verification
Before removal, verify:
1. `grep -r "docs/examples/" docs/ mkdocs.yml` returns no matches
2. All examples are identical or superseded in root `examples/`
3. No CI/CD scripts reference `docs/examples/`

## Non-Goals
- Not modifying content of examples (only removing duplicates)
- Not changing example code or documentation
- Not reorganizing other directories
