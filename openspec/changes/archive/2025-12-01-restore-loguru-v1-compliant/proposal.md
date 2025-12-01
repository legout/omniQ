# OpenSpec Change Proposal: Restore Loguru Enhanced Logging (v1 Compliant)

## Why
While standard logging meets simplicity requirements, Loguru provides critical production features that benefit even v1: better error handling, structured logging, automatic log rotation, and improved developer experience. These features enhance reliability and debuggability without significantly compromising understandability. The previous removal was an over-correction that sacrificed too much practical value for a task queue system.

## What Changes
- Restore Loguru dependency with simplified configuration (~80 lines vs previous 310)
- Keep Loguru but with streamlined API focused on v1 needs (4 public functions max)
- Maintain simple environment variable configuration (OMNIQ_LOG_LEVEL, OMNIQ_LOG_MODE)
- Preserve essential Loguru features: better formatting, error handling, structured logging
- Add task correlation IDs and execution tracing for production observability
- **BREAKING**: Re-add Loguru dependency
- **BREAKING**: Enhanced logging output format (JSON in PROD mode)

## Impact
- Affected specs: omniq-logging (enhanced rewrite)
- Affected code: `src/omniq/logging.py`, `src/omniq/core.py`
- Dependencies: Add loguru dependency back to pyproject.toml
- Configuration: Enhanced logging with smart defaults

## Files to Change

### Modified Files
- `src/omniq/logging.py` - Restore Loguru with simplified API (~80 lines)
- `src/omniq/core.py` - Update to use enhanced logging (optional task context)
- `pyproject.toml` - Re-add Loguru dependency
- `test_logging.py` - Update tests for Loguru features
- `MIGRATION_GUIDE.md` - Update for standard → Loguru migration
- `README.md` - Update documentation for Loguru features

### New Files
- None (enhancing existing files)

## Testing Strategy

- Unit tests for Loguru configuration and features
- Integration tests for enhanced error handling and task correlation
- Performance tests for Loguru vs standard logging impact
- Backward compatibility tests for existing simplified API
- Production scenario tests for log rotation and structured output

## Documentation Updates

- Update migration guide for standard → Loguru transition
- Add Loguru feature documentation to README
- Update API documentation with enhanced logging examples
- Add troubleshooting guide for Loguru-specific issues

## OpenSpec Validation

```bash
openspec validate --strict
```

## Approval

- [ ] Technical review completed
- [ ] API compliance verified (4 public functions max)
- [ ] Performance impact assessed (<5% overhead)
- [ ] Tests passing
- [ ] Documentation updated

---

**Change ID**: `restore-loguru-v1-compliant`  
**Date**: 2025-12-01  
**Priority**: HIGH (production readiness)  
**Breaking Change**: Minor (enhanced logging format, re-added dependency)