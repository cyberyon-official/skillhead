# skillhead — shared vocabulary

The words the `issue` and `loop-issues` skills, their agents and their
hooks use for roles, artefacts and gates. A skill, a spawn prompt or a
report names a role or a gate with these words.

## Language

### Roles (loop-issues)

**Orchestrator**:
The session that runs the loop: selects, locks, spawns, relays one-liners, checks gates, merges. After Step 0 it never reads the source code.
_Avoid_: supervisor, main agent

**Builder**:
The `loop-builder` agent. One phase per spawn, each in a fresh context: `contract`, one `build <k>` per slice, then `ship`. It writes the code and decides every finding's disposition.
_Avoid_: implementer, coder, fixer

**Contract reviewer**:
The `loop-contract-reviewer` agent. Reviews the contract once per issue, before any code: the substance is decided there.

**Shipper**:
The `loop-shipper` agent. Runs the mechanical phases — `pack`, `deliver`, `publish` — and judges nothing about code.

**Reviewer**:
The `loop-reviewer` agent. Read-only, one spawn per review round; reports findings with a proposed remedy and never edits.
_Avoid_: corrector

**Mechanic**:
The `loop-mechanic` agent. Mechanical work inside a worktree: tests from a closed list, codegen, brakes, the merge-queue head's merge.

**QA executor**:
The `loop-qa` agent. Drives the real application at the closing, spawns the **Breakers**, and returns GO / GO-PROVISIONAL / NO-GO / ABORTED.
_Avoid_: tester

**Breaker**:
An agent the QA executor spawns to break the application on hostile inputs, each in its own organization.

**Publisher**:
The `issue-publisher` agent: the only caller allowed to create issues on a guarded repo.

### Artefacts and mechanics

**Contract**:
The file the builder writes in its `contract` phase: `## Need` (one `N<k>` line per acceptance criterion), `## Shapes`, `## Reuses`, `## Tests`, `## Changed tests`, `## E2e impact`, `## Slices`. Every later phase follows it and names each departure under `## Deviations from plan`.
_Avoid_: spec, plan

**Lot**:
One issue's run through the loop, from contract to merge into the integration branch.

**Slot**:
A numbered lane of the loop with its own worktree, database and QA ports; slot 1 by default, more only when the user asks for parallel loops.

**Integration branch**:
`loop/<UTC date>`: every lot merges there; only the closing MR reaches the default branch.

**One-liner**:
The single output line of a child agent (verdict + report path). A report copied verbatim elsewhere is a process failure.

**Gate**:
A blocking condition before push or merge: lint, the review/fix loop converged, QA GO or GO-PROVISIONAL.

**Convergence**:
The review round where the reviewer reports nothing above `nit` (cap 3 rounds; cap reached → flagged draft, never merged).

**Disposition**:
The builder's ruling on each finding — `fixed`, or `unpaid — <reason>` listed under `## Unpaid findings`.

**Brake**:
Anything that slows a phase: a budget overrun (🐢, logged in `slowness.md`), a damaged build cache, a usage limit.

**Launch pack**:
The repo's `.claude/skills/verify/SKILL.md`: gates, per-slot values, how to start, seed and probe the QA stack.

**Profile**:
The repo's `.claude/loop-issues.json`, read by the hooks: test and gate commands, frontend and generated paths, toolchain notes.

## Relationships

- The **Orchestrator** spawns every agent; only the **QA executor** spawns agents of its own, its **Breakers**.
- The **Contract** feeds the **Contract reviewer**, every **Builder** phase, the **Reviewer** and the **QA executor**.
- Every **Lot** merges into the **Integration branch**; the closing runs the full **Gates** and one QA there, then opens one MR to the default branch.
- Child notifications always reach the **Orchestrator**, which relays only the **One-liner**.

## Flagged ambiguities

- "implementer" and "fixer" once named two roles — resolved: one **Builder**, from worktree to push.
- "plan" once meant both the implementation plan and the QA plan — resolved: one **Contract**; the QA plan is the Breaker map written at `ship`.
