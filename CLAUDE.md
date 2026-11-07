# skillhead

This file points; it rules nothing itself. Each rule lives in exactly one
place, and this file stays under 5 kB (guard `claude_md_ceiling`).

## Before acting, read

| When | Read |
|---|---|
| Before any code | `CODING_STANDARDS.md`, then the `docs/agents/` guide of the domain you touch |
| To name anything: code, API, database | `CONTEXT.md` |
| Before settling an architecture question | `docs/adr/README.md` and the decision at hand |
| Any interface or user-facing text work | `DESIGN.md`, `docs/ux-writing/README.md` |
| An unclear product case | `PRODUCT.md` |
| Before any review finding | `docs/review-checklist.md` |
| Writing or changing a test | `docs/testing.md`, `docs/tests-e2e.md` |
| Running the app, doing QA | `.claude/skills/verify/SKILL.md` |

## Verify

- `python3 ci/check.py` is the merge gate. It runs the steps of
  `ci/gates.json` (check, lint, test, build), then the guards of
  `ci/guards/`. Red means no merge.
- A step runs exactly as `ci/gates.json` writes it: no workaround flag
  (skip, retry, single thread). The cause gets fixed.

## Where to write

Write a rule, a decision, a vocabulary word or a recurring review
remark: in the present tense, in the one place the table above names,
in the same MR as the code that motivates it.

Never a date, an MR or issue number, or a former version: Git keeps the
history (guard `rules_have_no_history`).

## Improve the setup, not just the code

1. A review finding cites the rule it applies.
2. No rule yet? It gets written in its one place, in the same MR.
3. As soon as a machine can check it, it becomes a check: a guard in
   `ci/guards/` or a lint rule. Never prose alone.

## Agent loop

loop-issues: draft

- Forge: github. Default branch: `main`.
- Issues: `/skillhead:issue`. Implementation: `/skillhead:loop-issues` (plugin `skillhead`).
- Hook profile: `.claude/loop-issues.json`.
