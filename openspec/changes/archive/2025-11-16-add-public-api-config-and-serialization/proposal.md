## Why
Developers interact with OmniQ primarily through a high-level API and simple configuration. The PRD defines `AsyncOmniQ` / `OmniQ`, a small `Settings` model with env overrides, and a serializer abstraction with msgspec as the default and cloudpickle as an unsafe opt-in. A focused spec is needed to keep this surface area small and predictable.

## What Changes
- Define the public interface APIs for `AsyncOmniQ` and `OmniQ`, including enqueue, result retrieval, and worker creation.
- Specify the `Settings` model, its default values, and how environment variables override configuration.
- Describe serializer selection and behavior for msgspec (safe default) and cloudpickle (unsafe opt-in).
- Capture basic logging expectations, including the use of standard Python logging and `OMNIQ_LOG_LEVEL`.

## Impact
- Gives users a clear, stable way to configure and use OmniQ in v1.
- Keeps configuration simple (code-first plus a few env vars) while providing clear seams for future config providers.
- Makes the default safe serializer explicit while acknowledging the risks of the unsafe mode.
