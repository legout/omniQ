# Tasks: Replace Standard Logging with Loguru

1. **Add loguru dependency** ✅
   - [x] Update `pyproject.toml` to include `loguru` in dependencies
   - [x] Verify the dependency can be installed

2. **Update core.py logging** ✅
   - [x] Replace `import logging` with `from loguru import logger`
   - [x] Remove the `_configure_logging()` method from `AsyncOmniQ`
   - [x] Replace all `self._log` usage with direct `logger` calls
   - [x] Update log level configuration to work with loguru

3. **Update worker.py logging** ✅
   - [x] Replace `import logging` with `from loguru import logger`
   - [x] Replace all `self._log` usage with direct `logger` calls
   - [x] Ensure exception logging works properly with loguru

4. **Update configuration integration** ✅
   - [x] Modify settings handling to configure loguru log level
   - [x] Ensure log level changes from settings are applied correctly
   - [x] Test that log level configuration works as expected

5. **Test the changes** ✅
   - [x] Run existing tests to ensure no regressions
   - [x] Verify log output formatting is improved
   - [x] Test exception logging and traceback formatting
   - [x] Ensure log level configuration works through settings

6. **Validation** ✅
   - [x] Verify all logging statements work correctly
   - [x] Check that log levels are respected
   - [x] Ensure no logging-related errors occur
   - [x] Validate that the public API behavior is unchanged