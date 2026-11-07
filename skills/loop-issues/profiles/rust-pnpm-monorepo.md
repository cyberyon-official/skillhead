# Toolchain notes — Rust (mbx) + pnpm monorepo

Example for the profile key `toolchain_notes`: copy into the target repo
(e.g. `.claude/loop-issues-toolchain.md`) and point the profile at it.
These rules were inline in `loop-issues` before it was generalized.

- `CARGO_TARGET_DIR` stays unset, in every spawn and every gate: `cargo`
  goes through the `mbx` shim, which gives each worktree its managed
  target (linked as `apps/api/target`), restores compiled work from its
  store and prunes it itself. Never a `build-cache-*` nor a
  `target-slot-*`, never a `CARGO_TARGET_DIR` in a spawn prompt.
- `ci/check` refusing to run for want of mbx → `mbx doctor`.
- Damaged artefacts (E0463, E0460, a `.rlib` or `.rmeta` not found,
  typically after the disk filled) → `mbx doctor`, then
  `cargo clean -p <crate>` of the crates the error names, replay once.
  `cargo clean` of a whole target, mass `touch`, `CARGO_INCREMENTAL=0`,
  `rm -rf target/*` stay forbidden.
- Builder compile check while writing: `cargo check -p <crate>
  --all-targets` (`--features test-util` when the crate declares it),
  `pnpm check` for the webapp.
- Lint gate: `comply` (`ci/lib/comply-added` counts added lines only).
