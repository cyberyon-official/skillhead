# E2e tests

- **Everything a user can do or see has its e2e test.**
- **E2e tests run in parallel, in a real browser**, each with its own data: none depends on another.
- **An e2e test carries the gesture that breaks**: a `— broken gesture: <what the user can no longer do> —` line in the lot's contract.
- **On every release, the suite runs against the published image**, not the source.
- **Location and command:** <e2e folder, the command that runs them, how to target one file>.

QA proves it works today; the e2e test proves it over time.
