## 1. Spec
- [x] Update `omniq-api-config` to reflect the chosen `enqueue` API shape
- [x] Add scenarios for callable enqueue and (if supported) explicit `func_path` enqueue

## 2. Documentation
- [x] Update `README.md` quick start and task management examples to match the implemented API
- [x] Update retry budget semantics documentation
- [x] Add testing section to README with pytest usage
- [x] Update any `examples/` code to match
  - Fixed examples/basic_retry_example.py to use `from omniq.*` imports instead of `from src.omniq.*`

## 3. Validation
- [x] Run `openspec validate update-public-api-docs --strict`

