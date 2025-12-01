# OpenSpec Implementation Order Plan

## Overview

This document outlines the recommended implementation order for the remaining openspec change proposals, excluding the logging proposals which are already implemented.

## Current State Analysis

**Already Implemented:**
- ✅ `AsyncTaskQueue` class exists in `src/omniq/queue.py`
- ✅ Basic storage interface exists in `src/omniq/storage/base.py`
- ✅ Task models exist but have type inconsistencies
- ✅ Logging is fully implemented and compliant

**Critical Issues Identified:**
- Storage interface missing `get_task()` method (has placeholder returning `None`)
- Task model uses `int` for interval instead of `timedelta`
- Missing `TaskError` model
- Worker compatibility broken
- API compliance issues (serializer, constructors)

## Recommended Implementation Order

### **Phase 1: Foundation Fixes (Critical Path)**

#### 1. **Fix Storage Interface for Retry Support** 
**Priority: CRITICAL** | **Risk: LOW** | **Change ID: `fix-storage-interface-for-retry-support`**

**Why First:**
- AsyncTaskQueue already exists but can't function correctly
- Required by retry logic and interval task functionality
- No dependencies on other changes
- Foundation for proper queue operations

**Impact:**
- Adds missing `get_task()` and `reschedule_task()` methods to BaseStorage
- Enables proper retry and interval task functionality
- No breaking changes to existing APIs
- Fixes core queue functionality

**Files to Change:**
- `src/omniq/storage/base.py` - Add missing abstract methods
- `src/omniq/storage/sqlite.py` - Implement new methods
- `src/omniq/storage/file.py` - Implement new methods
- `src/omniq/queue.py` - Remove fallback methods

#### 2. **Fix Task Interval Type Compliance**
**Priority: CRITICAL** | **Risk: MEDIUM** | **Change ID: `task-interval-fix`**

**Why Second:**
- Core model inconsistency breaking spec compliance
- Depends on storage interface for complete interval task support
- Independent of worker interface changes
- Critical for spec compliance

**Impact:**
- Changes Task model field type from `int` to `timedelta`
- Requires serialization updates
- Affects interval task creation and handling
- **BREAKING**: Task model interface change

**Files to Change:**
- `src/omniq/models.py` - Update interval field type
- `src/omniq/serialization.py` - Update timedelta serialization
- `src/omniq/queue.py` - Fix interval handling in AsyncTaskQueue

#### 3. **Add Missing Task Models (TaskError)**
**Priority: HIGH** | **Risk: MEDIUM** | **Change ID: `add-missing-task-models`**

**Why Third:**
- Completes error handling model required by v1 spec
- Depends on Task model changes from interval fix
- Independent of storage and worker changes
- Essential for PRD compliance

**Impact:**
- Adds TaskError model with comprehensive error information
- Updates Task model to include optional error field
- Standardizes error handling across components
- **BREAKING**: Task model gains new error field (backward compatible)

**Files to Change:**
- `src/omniq/models.py` - Add TaskError model, update Task model
- `src/omniq/worker.py` - Update error handling to use TaskError
- `src/omniq/core.py` - Update error handling to use TaskError
- `src/omniq/storage/*.py` - Update error serialization

### **Phase 2: User Experience & Compliance**

#### 4. **Fix Worker Compatibility**
**Priority: HIGH** | **Risk: LOW** | **Change ID: `worker-compatibility-fix`**

**Why Fourth:**
- Restores backward compatibility for existing users
- Depends on AsyncTaskQueue (already complete)
- Independent of storage and model changes
- Focuses on user migration experience

**Impact:**
- Restores backward compatibility in AsyncWorkerPool constructor
- Adds deprecation warnings for old interface
- Improves user migration experience
- **NO BREAKING**: Maintains backward compatibility

**Files to Change:**
- `src/omniq/worker.py` - Update AsyncWorkerPool constructor
- `src/omniq/core.py` - Update AsyncOmniQ worker creation
- Documentation - Update migration guide and examples

#### 5. **Fix v1 API Compliance**
**Priority: HIGH** | **Risk: MEDIUM** | **Change ID: `fix-v1-api-compliance`**

**Why Fifth:**
- Multiple API compliance issues need resolution
- Depends on TaskError model and configuration stability
- Critical for full v1 spec compliance
- Affects core API behavior

**Impact:**
- Fixes default serializer to "msgspec" for security compliance
- Adds `OmniQ.from_env()` convenience constructor
- Fixes SQLite backend to properly use `db_url` setting
- **BREAKING**: Default serializer change affects task serialization

**Files to Change:**
- `src/omniq/config.py` - Fix default serializer, add validation
- `src/omniq/core.py` - Add from_env constructor
- `src/omniq/models.py` - TaskError already added in step 3
- `src/omniq/storage/sqlite.py` - Fix db_url usage

### **Phase 3: Optimization**

#### 6. **Simplify Task Status Transitions**
**Priority: MEDIUM** | **Risk: LOW** | **Change ID: `simplify-task-status-transitions`**

**Why Last:**
- Performance and simplicity improvement
- Depends on stable Task model from earlier phases
- Doesn't block core functionality or compliance
- Optimizes existing working code

**Impact:**
- Reduces complexity by ~70%
- Improves status transition performance by ~50%
- Simplifies codebase for better maintainability
- **MINOR BREAKING**: Some invalid transitions will be rejected

**Files to Change:**
- `src/omniq/models.py` - Simplify status validation logic
- `src/omniq/core.py` - Update status transition handling
- `src/omniq/storage/*.py` - Update storage validation if needed

## Dependency Graph

```
Phase 1: Foundation
├── Storage Interface Fix (no dependencies)
├── Task Interval Type Fix (depends on storage interface)
└── TaskError Model (depends on task model stability)

Phase 2: Compliance  
├── Worker Compatibility (depends on AsyncTaskQueue)
└── API Compliance (depends on TaskError, config)

Phase 3: Optimization
└── Status Transitions (depends on stable models)
```

## Risk Assessment by Phase

### Phase 1 (Foundation)
- **Storage Interface**: Low risk (additive changes only)
- **Task Interval Type**: Medium risk (breaking type change)
- **TaskError Model**: Medium risk (model expansion)

### Phase 2 (Compliance)
- **Worker Compatibility**: Low risk (backward compatible)
- **API Compliance**: Medium risk (multiple breaking changes)

### Phase 3 (Optimization)
- **Status Transitions**: Low risk (performance improvement)

## Implementation Timeline Estimate

**Phase 1 (Weeks 1-2)**: Foundation fixes
- Week 1: Storage interface + Task interval type
- Week 2: TaskError model + comprehensive testing

**Phase 2 (Weeks 3-4)**: User experience and compliance
- Week 3: Worker compatibility + API compliance part 1
- Week 4: API compliance completion + integration testing

**Phase 3 (Week 5)**: Optimization and polish
- Status transitions + performance testing + documentation updates

## Success Criteria

### After Phase 1:
- [ ] Retry logic works end-to-end
- [ ] Interval tasks function correctly with `timedelta`
- [ ] TaskError model implemented and tested
- [ ] All storage backends support new interface

### After Phase 2:
- [ ] Existing user code works without changes
- [ ] Full v1 API compliance achieved
- [ ] Configuration and serialization work correctly
- [ ] Migration path is clear for users

### After Phase 3:
- [ ] Performance improvements validated (≥40% improvement)
- [ ] Status transitions simplified and tested
- [ ] All tests passing with >90% coverage
- [ ] Documentation updated for all changes

## Rollback Considerations

### Phase 1 Changes
- **Storage Interface**: Easy rollback (remove new methods)
- **Task Interval Type**: Complex rollback (model changes, data migration)
- **TaskError Model**: Medium rollback (model changes)

### Phase 2 Changes
- **Worker Compatibility**: Simple rollback (revert constructor)
- **API Compliance**: Medium rollback (multiple config changes)

### Phase 3 Changes
- **Status Transitions**: Simple rollback (revert validation logic)

## Final Notes

This implementation order prioritizes:
1. **Fixing broken functionality first** (storage, task models)
2. **Achieving compliance second** (API, worker compatibility)
3. **Optimizing last** (performance, simplicity)

The order minimizes risk by building functionality incrementally, ensuring each change enables the next one while maintaining system stability throughout the process.