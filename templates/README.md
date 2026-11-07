# Project template

The starting structure for any project driven by `/issue` and
`/loop-issues`, whatever the stack: the project brings its commands; the
template brings one place for each rule and the guards that hold them.

```sh
python3 new_project.py ../my-project --name "My project" --forge gitlab --mode draft
python3 new_project.py ../existing-project   # adds, never overwrites
```

| File | Role | Read by |
|---|---|---|
| `CLAUDE.md` (+ `AGENTS.md`) | "When → what to read" table, under 5 kB; the `loop-issues: draft\|automerge` line | every agent, every turn |
| `CODING_STANDARDS.md` → `docs/agents/*.md` | Index of the guides; one rule per line, with its check | builder, reviewer |
| `CONTEXT.md` | Domain vocabulary, one name per concept | everyone, to name things |
| `docs/adr/` | Numbered, indexed architecture decisions | `/issue` (recon), builder |
| `PRODUCT.md`, `DESIGN.md`, `docs/ux-writing/` | Product, interface and text rules | builder, QA |
| `docs/review-checklist.md` | Numbered findings, stable numbers | reviewer |
| `docs/testing.md`, `docs/tests-e2e.md` | Test rules; one e2e test per visible behaviour | builder, contract |
| `.claude/skills/verify/SKILL.md` | Launch pack: gates, per-slot values, QA stack | orchestrator, shipper, `qa` |
| `.claude/loop-issues.json` | Hook profile | `/loop-issues` hooks |
| `ci/gates.json` + `ci/check.py` | Merge gate: the stack's steps, then the guards | humans, CI, the loop's closing |
| `ci/guards/` | Architecture tests on the repo itself | `ci/check.py` |

Guards provided (generic): `CLAUDE.md` under 5 kB, pointers that exist, no
date or issue/MR number in the rules, guide index up to date, checklist
numbered without gaps, unique vocabulary terms, numbered and indexed
ADRs, and a test of the gate runner itself. `ci/guards/_repo.py`
documents the pattern for a project's own architecture tests
(occurrences counted, exceptions listed with their reason).

Fill in after generating: `ci/gates.json`, `docs/agents/toolchain.md`,
`.claude/skills/verify/SKILL.md`, `CONTEXT.md`, `PRODUCT.md`, `DESIGN.md`.
