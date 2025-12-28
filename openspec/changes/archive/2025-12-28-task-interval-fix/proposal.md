# Fix Task Interval Type Compliance

## Overview

Fix critical type inconsistency in Task model where `interval` field is defined as `int` but v1 spec requires `timedelta`. This breaks serialization and interval task handling.

## Problem Statement

**Current Issue:**
- Task model has `interval: int` field
- v1 spec requires `interval: timedelta` field
- AsyncTaskQueue expects `timedelta` but receives `int`
- Serialization/deserialization breaks for interval tasks

**Impact:**
- Interval tasks cannot be created properly
- Serialization fails for interval tasks
- v1 spec non-compliance

## Root Cause Analysis

The Task model was updated to include interval field but used wrong type:
- Models.py: `interval: int = 0`
- Should be: `interval: timedelta = None`

## Proposed Solution

### 1. Update Task Model
- Change `interval` field type from `int` to `timedelta`
- Update default value to `None`
- Add proper type validation

### 2. Update Serialization
- Ensure `timedelta` objects serialize properly
- Update deserialization to handle `timedelta`

### 3. Update AsyncTaskQueue
- Fix interval task creation to use `timedelta`
- Update interval conversion logic

## Implementation Plan

### Phase 1: Model Updates
1. Update Task model interval field type
2. Add proper type hints and validation
3. Update model creation methods

### Phase 2: Serialization Updates
1. Update serialization for timedelta fields
2. Update deserialization for interval tasks
3. Add proper error handling

### Phase 3: Queue Integration
1. Fix AsyncTaskQueue interval handling
2. Update interval task creation
3. Fix interval conversion logic

## Files to Change

### Core Files
- `src/omniq/models.py` - Update Task model interval field
- `src/omniq/serialization.py` - Update timedelta serialization
- `src/omniq/queue.py` - Fix interval handling in AsyncTaskQueue

### Test Files
- Update relevant tests for interval type changes
- Add interval task serialization tests

## Risk Assessment

**Breaking Changes:**
- Task model interface changes (type change)
- Existing interval task data may need migration

**Mitigation:**
- Provide migration path for existing data
- Update all references consistently
- Add comprehensive tests

## Success Criteria

- [ ] Task model uses `timedelta` for interval field
- [ ] Interval tasks serialize/deserialize correctly
- [ ] AsyncTaskQueue handles interval tasks properly
- [ ] All tests pass with new interval type
- [ ] v1 spec compliance achieved

## Dependencies

- Depends on storage interface fixes (for complete interval task support)
- Must be implemented before worker compatibility fixes

## Testing Strategy

1. Unit tests for Task model interval field
2. Serialization tests for timedelta objects
3. Integration tests for interval task creation
4. AsyncTaskQueue interval handling tests

## Rollback Plan

If issues arise:
1. Revert Task model to `int` interval
2. Revert serialization changes
3. Restore AsyncTaskQueue interval logic
4. Document migration requirements

## Alternatives Considered

1. **Keep int, convert everywhere**: More complex, violates spec
2. **Add both fields**: Redundant, confusing interface
3. **Use Union[int, timedelta]**: Type safety issues

**Chosen approach:** Direct `timedelta` type for spec compliance and clarity.