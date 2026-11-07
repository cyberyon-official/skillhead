# Tests

- **A test proves a behaviour, not an implementation.** It survives a refactor that changes nothing observable.
- **A test is deterministic.** No sleep, no real clock, no network, no dependency on execution order: clock and randomness are injected.
- **One fake per interface, shared by every test.** Two doubles of the same port diverge.
- **The name says the bug that would slip through if it broke.**
- **Every need of an issue has its test**; a behaviour the user can see also has its e2e test (`docs/tests-e2e.md`).
- **Layers:** <unit: where and how; integration: real database or not; e2e: see `docs/tests-e2e.md`>.
