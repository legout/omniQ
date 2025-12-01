# Implementation Tasks

## Phase 1: Constructor Updates
- [x] Add `queue: AsyncTaskQueue | None = None` parameter
- [x] Add `storage: BaseStorage | None = None` parameter (deprecated)
- [x] Add `logger: Logger | None = None` parameter
- [x] Implement parameter validation logic
- [x] Add dual interface handling logic
- [x] Add proper error messages for invalid parameter combinations

## Phase 2: Deprecation System
- [x] Import `warnings` module
- [x] Add deprecation warning for `storage` parameter
- [x] Create helpful warning message with migration guidance
- [x] Add proper stacklevel for warning location
- [x] Test deprecation warning functionality

## Phase 3: Internal Queue Creation
- [x] Add `_create_queue_from_storage()` method
- [x] Add `_validate_parameters()` method
- [x] Add `_validate_types()` method
- [x] Ensure proper logger propagation
- [x] Handle queue creation errors gracefully

## Phase 4: Core Integration Updates
- [x] Update `AsyncOmniQ` to use new `queue` parameter
- [x] Ensure internal consistency in core
- [x] Update any other internal worker creation
- [x] Verify worker initialization works correctly

## Phase 5: Testing
- [x] Add tests for new `queue` interface
- [x] Add tests for old `storage` interface with deprecation warning
- [x] Add tests for error conditions (both parameters, neither parameter)
- [x] Add tests for parameter validation
- [x] Add integration tests with `AsyncOmniQ`
- [x] Add worker task execution tests for both interfaces
- [x] Add type validation tests

## Phase 6: Documentation
- [x] Update AsyncWorkerPool API documentation
- [x] Add deprecation notice to docstring
- [x] Add examples for both interfaces
- [x] Update migration guide with worker changes
- [x] Add deprecation timeline information
- [x] Update examples throughout codebase

## Validation Criteria
- [x] Existing code continues to work without changes
- [x] New queue interface works as designed
- [x] Deprecation warnings displayed appropriately
- [x] Clear error messages for invalid usage
- [x] Migration path is clear and documented
- [x] All tests pass for both interfaces
- [x] No performance regression for new interface
- [x] AsyncOmniQ integration works seamlessly