# Implementation Tasks

## Phase 1: Constructor Updates
- [ ] Add `queue: AsyncTaskQueue | None = None` parameter
- [ ] Add `storage: BaseStorage | None = None` parameter (deprecated)
- [ ] Add `logger: Logger | None = None` parameter
- [ ] Implement parameter validation logic
- [ ] Add dual interface handling logic
- [ ] Add proper error messages for invalid parameter combinations

## Phase 2: Deprecation System
- [ ] Import `warnings` module
- [ ] Add deprecation warning for `storage` parameter
- [ ] Create helpful warning message with migration guidance
- [ ] Add proper stacklevel for warning location
- [ ] Test deprecation warning functionality

## Phase 3: Internal Queue Creation
- [ ] Add `_create_queue_from_storage()` method
- [ ] Add `_validate_parameters()` method
- [ ] Add `_validate_types()` method
- [ ] Ensure proper logger propagation
- [ ] Handle queue creation errors gracefully

## Phase 4: Core Integration Updates
- [ ] Update `AsyncOmniQ` to use new `queue` parameter
- [ ] Ensure internal consistency in core
- [ ] Update any other internal worker creation
- [ ] Verify worker initialization works correctly

## Phase 5: Testing
- [ ] Add tests for new `queue` interface
- [ ] Add tests for old `storage` interface with deprecation warning
- [ ] Add tests for error conditions (both parameters, neither parameter)
- [ ] Add tests for parameter validation
- [ ] Add integration tests with `AsyncOmniQ`
- [ ] Add worker task execution tests for both interfaces
- [ ] Add type validation tests

## Phase 6: Documentation
- [ ] Update AsyncWorkerPool API documentation
- [ ] Add deprecation notice to docstring
- [ ] Add examples for both interfaces
- [ ] Update migration guide with worker changes
- [ ] Add deprecation timeline information
- [ ] Update examples throughout codebase

## Validation Criteria
- [ ] Existing code continues to work without changes
- [ ] New queue interface works as designed
- [ ] Deprecation warnings displayed appropriately
- [ ] Clear error messages for invalid usage
- [ ] Migration path is clear and documented
- [ ] All tests pass for both interfaces
- [ ] No performance regression for new interface
- [ ] AsyncOmniQ integration works seamlessly