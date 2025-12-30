# Design: Diátaxis content boundaries (users only)

## Diátaxis rules of thumb
- Tutorials: learning-oriented, sequential, minimal branching; assumes a fresh user.
- How-to: goal-oriented recipes; assumes basic familiarity; focuses on "how to do X".
- Reference: factual, complete, stable, low narrative; generated API + curated config/env.
- Explanation: conceptual; reasons, tradeoffs, mental models; not a step-by-step recipe.

## Content sourcing
- Tutorials SHOULD reuse the runnable examples under `examples/` as the canonical executable source.
- Documentation MUST NOT require external infrastructure beyond what OmniQ provides in v1 (e.g. SQLite is optional; no network services).

## API reference expectations
- mkdocstrings output MUST include power-user modules (queue/worker/storage) in the Reference nav.
- Reference pages should not require importing optional/test-only dependencies.

## Consistency constraints
- Names and signatures MUST match the implemented API.
- Prefer linking between sections rather than duplicating explanations.
