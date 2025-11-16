# Replace Standard Logging with Loguru

## Summary

Replace Python's standard `logging` module with `loguru` throughout the OmniQ codebase to provide better logging capabilities with simpler configuration and improved output formatting.

## Motivation

The current standard logging implementation requires manual configuration and has limited formatting options. Loguru offers:
- Simpler setup with no boilerplate configuration
- Better default formatting and colors
- Built-in exception handling and traceback formatting
- Easy log rotation and compression
- Better async support
- Cleaner, more readable log output

## Scope

This change will:
1. Add `loguru` as a project dependency
2. Replace all `logging` imports with `loguru`
3. Remove the custom `_configure_logging()` method from `AsyncOmniQ`
4. Update all logger usage to use loguru's simplified API
5. Ensure log level configuration still works through settings

## Files Affected

- `pyproject.toml` - Add loguru dependency
- `src/omniq/core.py` - Replace logging imports and configuration
- `src/omniq/worker.py` - Replace logging imports

## Backward Compatibility

This is an internal implementation change that should not affect the public API. Log levels configured through settings will continue to work as expected.

## Testing

- Verify all existing functionality works with loguru
- Test log level configuration through settings
- Ensure log output is properly formatted
- Verify exception logging and tracebacks work correctly