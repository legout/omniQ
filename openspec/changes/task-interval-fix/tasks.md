# Implementation Tasks

## Phase 1: Task Model Updates
- [ ] Change `interval` field type from `int` to `timedelta | None`
- [ ] Update default value from `0` to `None`
- [ ] Add field validator for backward compatibility (int → timedelta)
- [ ] Add proper type hints and imports
- [ ] Update Task model docstring

## Phase 2: Serialization Updates
- [ ] Add `serialize_timedelta()` function
- [ ] Add `deserialize_timedelta()` function
- [ ] Update Task serialization to handle interval field
- [ ] Update Task deserialization to handle interval field
- [ ] Add error handling for malformed timedelta data

## Phase 3: AsyncTaskQueue Updates
- [ ] Fix `add_interval_task()` method to accept `timedelta | int`
- [ ] Add interval conversion utilities
- [ ] Update interval scheduling logic to use timedelta
- [ ] Fix interval task rescheduling logic
- [ ] Add proper error handling for invalid intervals

## Phase 4: Core Integration
- [ ] Update AsyncOmniQ to handle interval tasks properly
- [ ] Ensure interval tasks work through the public API
- [ ] Update any interval-related utility functions
- [ ] Add interval validation where needed

## Phase 5: Testing
- [ ] Add unit tests for Task model interval field changes
- [ ] Add tests for interval field validator (int → timedelta)
- [ ] Add serialization tests for timedelta objects
- [ ] Add AsyncTaskQueue interval task creation tests
- [ ] Add interval task execution tests
- [ ] Add backward compatibility tests (int intervals)
- [ ] Add error handling tests for invalid intervals

## Phase 6: Documentation and Migration
- [ ] Update Task model API documentation
- [ ] Document interval field type change
- [ ] Add migration examples for existing code
- [ ] Update AsyncTaskQueue documentation
- [ ] Add interval task examples to documentation
- [ ] Update changelog with breaking change notice

## Validation Criteria
- [ ] Task model uses `timedelta | None` for interval field
- [ ] Interval tasks serialize/deserialize correctly
- [ ] AsyncTaskQueue handles both `timedelta` and `int` intervals
- [ ] Backward compatibility maintained for `int` intervals
- [ ] All tests pass with new interval type
- [ ] v1 spec compliance achieved
- [ ] Documentation updated with examples