## Context

The current OmniQ logging implementation uses Python's standard `logging` module, which has several limitations:
- Verbose and complex configuration requiring multiple lines of code
- Limited structured logging capabilities
- No built-in exception formatting and traceback handling
- Inconsistent formatting across different Python versions
- Lack of modern features like automatic log rotation and colorization

Loguru offers a modern, simpler alternative with better defaults and enhanced capabilities that would improve the developer experience and debugging capabilities of OmniQ.

## Goals / Non-Goals

### Goals
- Simplify logging configuration and usage
- Add structured logging capabilities with contextual data
- Improve exception handling and formatting
- Maintain backward compatibility for existing users
- Enable better debugging and monitoring capabilities
- Support modern logging features like rotation and multiple handlers

### Non-Goals
- Completely remove the old logging API in v1 (maintain compatibility)
- Add complex logging pipelines or external log aggregation
- Implement custom log parsing or analysis tools
- Support Python versions below 3.13 (already a project requirement)

## Decisions

### Decision: Use Loguru as primary logging system
**Rationale**: Loguru provides better defaults, simpler configuration, and enhanced features like structured logging and automatic exception handling. It eliminates the boilerplate required by standard logging while providing more capabilities.

**Alternatives considered**:
- Keep standard logging: Would maintain status quo but miss out on modern features
- Use structlog: More complex configuration, steeper learning curve
- Custom logging solution: Would require significant maintenance and testing

### Decision: Maintain backward compatibility layer
**Rationale**: Existing users may have code that calls the current logging functions directly. A compatibility layer ensures smooth migration without breaking changes.

**Implementation**: Wrap Loguru calls in existing function signatures, deprecate old API gradually.

### Decision: Add loguru as required dependency
**Rationale**: Loguru is lightweight and has minimal dependencies. Making it required ensures consistent logging behavior across all installations.

**Alternatives considered**:
- Optional dependency: Would create inconsistent behavior
- Separate logging package: Would overcomplicate the architecture

## Risks / Trade-offs

### Risk: Dependency bloat
**Mitigation**: Loguru is lightweight (~100KB) with minimal dependencies. The benefits outweigh the size increase.

### Risk: Breaking existing user configurations
**Mitigation**: Maintain backward compatibility layer and provide clear migration documentation. Support both old and new environment variables during transition.

### Risk: Learning curve for users unfamiliar with Loguru
**Mitigation**: Provide comprehensive documentation and examples. Keep the compatibility layer so users can migrate gradually.

### Trade-off: Simplicity vs. Flexibility
Loguru prioritizes simplicity with sensible defaults, which may reduce some advanced configuration options available in standard logging. However, most use cases are covered better by Loguru's approach.

## Migration Plan

### Phase 1: Implementation
1. Add loguru dependency
2. Rewrite logging module using Loguru
3. Maintain all existing function signatures
4. Add new Loguru-specific configuration options

### Phase 2: Testing and Validation
1. Ensure all existing logging functions work identically
2. Test new structured logging capabilities
3. Validate exception handling improvements
4. Test environment variable configurations

### Phase 3: Documentation and Migration
1. Document new logging capabilities
2. Create migration guide for advanced users
3. Add examples of structured logging usage
4. Update API documentation

### Phase 4: Future Deprecation (v2+)
1. Deprecate old logging functions with warnings
2. Encourage migration to Loguru-native API
3. Eventually remove compatibility layer in major version bump

## Open Questions

- Should we support both `OMNIQ_LOG_LEVEL` (old) and `LOGURU_LEVEL` (new) environment variables, or standardize on one?
- How should we handle log rotation configuration - through environment variables or programmatic API?
- Should we expose Loguru's advanced features like interception and customization, or keep the API simple?

## Implementation Notes

### Key Changes Required
1. **Dependency Management**: Add `loguru` to `pyproject.toml`
2. **Module Rewrite**: Complete rewrite of `src/omniq/logging.py`
3. **Import Updates**: Update all `import logging` statements to `from loguru import logger`
4. **Configuration API**: New `configure_logging()` function using Loguru's `remove()` and `add()` methods
5. **Structured Logging**: Add support for contextual data in log messages

### Backward Compatibility Strategy
- Keep all existing function signatures unchanged
- Implement old functions as thin wrappers around Loguru
- Add deprecation warnings for advanced users who want to migrate
- Support existing environment variable names

### Testing Strategy
- Unit tests for all logging functions
- Integration tests with task execution workflows
- Configuration tests for environment variables
- Exception handling and formatting tests
- Performance tests to ensure no regression