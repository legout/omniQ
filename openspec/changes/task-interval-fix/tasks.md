# Implementation Tasks

## Phase 1: Task Model Updates
- [x] Change `interval` field type from `int` to `timedelta | None`
- [x] Update default value from `0` to `None`
- [x] Add field validator for backward compatibility (int → timedelta)
- [x] Add proper type hints and imports
- [x] Update Task model docstring

## Phase 2: Serialization Updates
- [x] Add `serialize_timedelta()` function
- [x] Add `deserialize_timedelta()` function
- [x] Update Task serialization to handle interval field
- [x] Update Task deserialization to handle interval field
- [x] Add error handling for malformed timedelta data

## Phase 3: AsyncTaskQueue Updates
- [x] Fix `add_interval_task()` method to accept `timedelta | int`
- [x] Add interval conversion utilities
- [x] Update interval scheduling logic to use timedelta
- [x] Fix interval task rescheduling logic
- [x] Add proper error handling for invalid intervals

## Phase 4: Core Integration
- [x] Update AsyncOmniQ to handle interval tasks properly
- [x] Ensure interval tasks work through the public API
- [x] Update any interval-related utility functions
- [x] Add interval validation where needed

## Phase 5: Testing
- [x] Add unit tests for Task model interval field changes
- [x] Add tests for interval field validator (int → timedelta)
- [x] Add serialization tests for timedelta objects
- [x] Add AsyncTaskQueue interval task creation tests
- [x] Add interval task execution tests
- [x] Add backward compatibility tests (int intervals)
- [x] Add error handling tests for invalid intervals

## Phase 6: Documentation and Migration
- [x] Update Task model API documentation
- [x] Document interval field type change
- [x] Add migration examples for existing code
- [x] Update AsyncTaskQueue documentation
- [x] Add interval task examples to documentation
- [x] Update changelog with breaking change notice

## Validation Criteria
- [x] Task model uses `timedelta | None` for interval field
- [x] Interval tasks serialize/deserialize correctly
- [x] AsyncTaskQueue handles both `timedelta` and `int` intervals
- [x] Backward compatibility maintained for `int` intervals
- [x] All tests pass with new interval type
- [x] v1 spec compliance achieved
- [x] Documentation updated with examples