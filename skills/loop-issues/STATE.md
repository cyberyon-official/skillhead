# state.md — the loop's memory

`<report-root>/state.md` is the only state a loop keeps between turns,
compactions and sessions: `/skillhead:loop-issues` in a fresh session resumes
from it. This file is its one grammar. SKILL.md and RENDEZVOUS.md say *when*
a line is written; the hooks (`skillhead state …`) parse it; neither restates
the syntax below. `test_spec.py` checks the example against the parser.

Times are UTC ISO-8601 (`date -u +%FT%TZ`). One line per item, in any order;
no other line: brakes and history go to `brakes.md`, findings to
`findings.md`.

| Line | Written by | Read by |
|---|---|---|
| `mode: run` \| `mode: drain` \| `mode: pause-until <time>` | Step 0 (new run: `run`); the user's words (SKILL.md § Rules); the closing request (`drain`) | `skillhead state tick` |
| `slot <s>: free` | Step 0, a slot's lot leaving | you |
| `slot <s>: #<n> <phase> <subagent_type> since <time> — <report dir>` | every spawn | `skillhead state tick` (budget 🐢, appended ` 🐢 <spent>/<budget> min`) |
| `slot <s>: #<n> <phase> <subagent_type> done — <report dir>` | the phase's notification (a finished phase never ages) | you |
| `planned: <N> (+<k>)` | Step 0 (`+0`), each issue the loop creates (`+1`) | `skillhead state count` |
| `queue: #<n> #<m> …` | Step 1 (the run's scope), each issue the loop creates | Step 1 |
| `done: #<n> <summary line>[ rework]` | Step 6, per finished lot | `skillhead state count` |
| `skip: #<n> — <reason>` | Step 1 (`blocked by #N`, `outside template`, a draft failure) | Step 1 |
| `held: contract #<n> — <disk reason>` | the disk check before a new lot | the next lot's notification (retried first) |
| `stopped: <disk\|model\|drained> — <reason>` | the loop's stops | Step 0 of the next session (dropped there) |
| `integration: <branch>` | Step 0 (none yet: `loop/<UTC date>`) | every phase (`<integration>`), the closing |
| `integrated: #<n> !<mr> <report-dir>` | Step 4, per lot merged into `<integration>` | Step 1 (`LOOP_INTEGRATED`), the closing |
| `closing: asked` | « close the loop », or the end of the queue | the closing |
| `facts: <path>` | Step 0 | every spawn (the Step 0 facts) |

A new run keeps `mode:`, `planned:`, `done:` of a run in flight and drops
`stopped:`; `integration:`, `integrated:` and `closing:` survive until the
closing merges, which deletes them. A slot's 🐢 stays while its phase is
unchanged.

## Example

```
mode: run
slot 1: #42 build-2 skillhead:loop-builder since 2026-11-08T07:30:00Z — /r/issue-42
slot 2: #43 review-1 skillhead:loop-reviewer done — /r/issue-43
slot 3: free
planned: 5 (+1)
queue: #42 #43 #44 #45 #46 #47
done: #41 ✅ merged into loop/2026-11-08
skip: #44 — blocked by #40
integration: loop/2026-11-08
integrated: #41 !12 /r/issue-41
facts: /r/step0.md
```
