# Guide: toolchain

Read by every `/loop-issues` agent (key `toolchain_notes` of
`.claude/loop-issues.json`). Fill it in for the project's stack.

- **Verification commands are the ones in `ci/gates.json`.** An agent never composes its own variant. Check: review.
- **A damaged build cache is repaired, never wiped whole.** <The stack's repair command.> Check: review.
- **Banned commands:** <e.g. wiping the whole cache, disabling incremental builds>. Check: review.
- **Dependencies:** <package manager, lockfile, rule for adding one>. Check: review.
