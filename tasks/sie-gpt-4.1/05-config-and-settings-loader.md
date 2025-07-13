<!-- @/tasks/05-config-and-settings-loader.md -->
# Subtask 1.5: Config and Settings Loader

**Objective:**  
Create a robust configuration loader supporting direct, dict, YAML, and environment variable-based configuration for all library components.

**Requirements:**  
- All settings constants are overridable with prefixed environment variables (`OMNIQ_`).
- YAML loader, config validation, and type conversion using `msgspec`.
- Support configuration for queues, storage, events, and workers.

**Context from Project Plan:**  
- Reference “Configuration” and “Settings and Environment Variables” sections.

**Deliverables:**  
- Comprehensive config loader and settings management under `src/omniq/config/`.