## MODIFIED Requirements

### Requirement: Retry Budget Enforcement
The system MUST enforce retry budgets consistently across all components.

#### Scenario: Attempts count total executions
- **GIVEN** a task with `attempts=0` on enqueue
- **WHEN** task is dequeued and transitions to `RUNNING`
- **THEN** `attempts` MUST increment to `1`
- **AND** `attempts` MUST represent total number of times task has been claimed for execution
- **AND** MUST NOT decrement or reset attempts for retry tasks

#### Scenario: Retry budget with "<" comparison
- **GIVEN** a task with `max_retries=3` and `attempts=2`
- **WHEN** task fails and is evaluated for retry
- **THEN** system MUST allow retry because `2 < 3` evaluates to `True`
- **AND** MUST schedule task for another execution attempt

#### Scenario: Retry budget exhausted with "<" comparison
- **GIVEN** a task with `max_retries=3` and `attempts=3`
- **WHEN** task fails and is evaluated for retry
- **THEN** system MUST stop retrying because `3 < 3` evaluates to `False`
- **AND** MUST mark task as final `FAILED` without additional retries
