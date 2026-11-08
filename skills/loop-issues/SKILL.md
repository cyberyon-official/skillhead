---
name: loop-issues
description: Standing implementation loop — autonomously implement the issues the invocation names (and those the loop creates), nothing else. Per issue — an opus builder in fresh phases (contract of shapes, build slices, ship), one opus contract review before any code, a sonnet shipper for pack and deliver (comply triage, MR), opus review rounds (ponytail-review + quality-bar-review) judged on unpaid shapes until convergence (cap 3), push as draft, merge into the run's integration branch after a workspace check, repeat; once that scope is drained or on « close the loop », full gates and one QA on that branch, then one MR to the default branch.
---

# Loop orchestrator

You orchestrate; you implement NOTHING. After Step 0, never read the
repo — no `git grep/show/diff/log`, no Read on project files, no full
issue bodies. Your only evidence: agent reports + forge API. Your only
memory: `<report-root>/state.md`, in the grammar of
`${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/STATE.md` — read it before you
write a line of it.

Briefs live next to this file: the builder reads
`${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/BUILDER.md`, the shipper
`${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/SHIPPER.md`, the contract reviewer
`${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/CONTRACT-REVIEW.md`, the code reviewer
`${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/REVIEW.md`; every agent reads
`${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/RENDEZVOUS.md` — the only way anyone waits or reports. Each
pinned agent already names its brief: a spawn prompt never renames
one (a `REVIEWER.md` that does not exist cost a `find` in 41
reviews). A spawn prompt hands facts and the
brief's absolute path, never a paraphrase of it — and never rewrites a
phase's gate scope: the brief decides it (the builder checks its
crates and writes its contract's tests without running them, `pack`
and `deliver` run comply only, a lot's merge into `<integration>`
runs the launch pack's merge command, and every other test, the full gates
and QA run once, on `<integration>`, at the closing (§ Closing —
user, 2026-10-20: no test per lot); a
prompt that asked for the full trio at pack cost ~15 min on one lot,
2026-09; four slots compiling the full gates per lot froze the
machine, 2026-10-15). `skillhead spawn_guard` refuses a phase prompt
that names a gate. A merge-queue red sends its lot back to `ship`; it
never widens the next lots' gates — a lesson that would goes to
`/reflect` on the brief.

## Agents

Every spawn names a pinned agent type and NEVER passes `model` (an
explicit `model` overrides the pin), `name` = `#<n> <phase> · <goal>`
and `description` = its purpose, never a file:

| Role | `subagent_type` | Model · effort | Spawned by | Budget (min) |
|---|---|---|---|---|
| builder (`contract`, `build <k>`, `ship`) | `skillhead:loop-builder` | opus 5.5 · medium | you, once per phase | 40 |
| contract reviewer | `skillhead:loop-contract-reviewer` | opus 5.5 · medium | you, ONCE per issue | — |
| shipper (`pack`, `deliver`, `publish`) | `skillhead:loop-shipper` | sonnet 5.5 · medium | you, once per phase | 60 |
| code reviewer | `skillhead:loop-reviewer` | opus 5.5 · medium | you, once per round | 15 |
| mechanic (tests of the closed list, codegen, brakes, the queue head's merge) | `skillhead:loop-mechanic` | sonnet 5.5 · medium | you, after a `build <k>` that lists tasks, on a brake, at the queue head | 15 |
| QA executor (Breakers only) | `skillhead:loop-qa` | opus 5.5 · medium | you, on `QA-READY` | 15 × lots ÷ N |

Budget = spawn → notification; `skillhead state tick` reads this column.

Builder phases: `contract`, one `build <k>` per slice, `ship`.
Shipper phases: `pack`, `deliver`, `publish`. The contract reviewer reviews it ONCE: the substance is decided there and costs no rework. Every phase is a
fresh context. Only YOU spawn: builder and shipper have no `Agent`
tool — a child's notification never resumes a subagent, it froze a
thread 30-60 min each time. Review rounds (pack, review, ship) run until `MERGEABLE`,
cap 3; QA runs once per closing, on every lot together (§ Closing).

There is NO path that spawns an implementer without a contract:
"spawn opus agents", "a wave of fixes", "catch-up" (in any language) mean
run THIS loop on those issues. Two bypasses: a fix under 15 lines
with no product choice — one agent commits, pushes and merges it, no
issue; or the user writes "hors loop" — say back what it costs (no
contract, no review, no cap) and wait for the confirmation.

Invoking this skill authorizes commits, pushes and draft MRs;
merging needs autonomous mode.

## Step 0 — Discover the project (once)

Rebuilt each run from this skill and the repo, never copied from a
previous run's Step 0 — repo docs/config only (CLAUDE.md, `package.json` scripts,
`Makefile`, `justfile`):

- **Forge** — `git rev-parse --show-toplevel` → `<main-repo>`;
  `git remote get-url origin` → forge + project path. GitLab →
  `glab api` (project `<group>%2F<project>`), narrowed queries;
  GitHub → `gh`. No MCP server in any agent of the loop. A checkout is matched on its remote,
  never on its directory name.
- **Fresh instructions** — every spawn starts in THIS checkout and
  loads its `CLAUDE.md` (and any `@` imports) on every turn, whatever worktree it
  then works in. `git fetch origin` then `git diff --quiet HEAD
  origin/<default> -- CLAUDE.md CODING_STANDARDS.md docs/agents` fails
  → stop before any spawn and ask the user to start the loop from a
  checkout of the default branch (a stale one cost ~45k tokens per turn
  of every agent, 06-08/10/2026). Then `skillhead state model
  <state.md> <the exact model ID of your system prompt>`: exit 2 →
  it wrote `stopped: model — …` in `state.md`; stop before any
  selection, one line `🐢 <its stderr>`; exit 1 (no pin) → the same
  line, stop. Then `skillhead state
  fresh`: exit 2 → re-read the skill files its stderr names before
  selecting; exit 0 → read nothing again.
- **Verification trio** — check + test + build commands and pinned
  tooling; a documented merge gate is law. The commands as the repo
  documents them: a workaround flag (`--test-threads 1`, a skip)
  never sticks to a gate, its cause is paid (DB migrated once before
  the run). Time the test gate once; above 5 min, find why now.
- **CI posture** — blocking MR pipeline? None → the trio IS the gate.
- **Certifying gate** — a repo script that runs the gates on a pushed
  sha and posts a status on it (a `local-gates`-style status the
  forge or the release checks): record its path and its status name.
  It is a superset of the trio, so it REPLACES the trio at the
  closing (§ Closing); none → the trio is the closing's gate.
- **Mode** — `loop-issues: automerge` documented in the repo →
  **autonomous** (labels, merges into `<integration>`, the closing
  MR merged once green); else **draft**: never write queue labels,
  never merge, every MR opens as a draft.
- **Integration branch** — `<integration>` = the `integration:` line
  of `state.md`; none → `loop/<UTC date>`, created from
  `origin/<default>` (`git push origin
  origin/<default>:refs/heads/loop/<date>`) and written there. Every
  lot builds on it and its MR targets it (`<base>` below means
  `<integration>`, or the stacked MR's branch); nothing reaches
  `<default>` but the closing MR. It lives in its own worktree
  `<worktrees dir>/loop-<date>` (env `loop-<date>.env` = slot 1's), created at the first merge and kept
  until the closing merges: its warm target makes each merge's check
  incremental.
- **Project profile** — `<main-repo>/.claude/loop-issues.json`
  (examples: `${CLAUDE_PLUGIN_ROOT}/skills/loop-issues/profiles/`): the hooks read
  from it the test and gate commands of this stack, the frontend and
  generated-path patterns. None → the hooks' generic defaults. Its
  `toolchain_notes` names a markdown file of the repo (none → skip)
  holding the toolchain's rules — build cache, target dirs, artefact
  repair, banned commands: read it here, and hand its path in every
  spawn; every agent obeys it like its brief.
- **Worktree wiring** — deps, `.env`, codegen a fresh worktree needs,
  per the toolchain notes. A
  slot `s` = 1 by default (§ Rules: sequential); with parallel loops
  asked, the lowest slot no issue in flight holds. Handed in
  every spawn of the issue. Disk is checked before a spawn, never
  before a gate (§ The loop). A slot
  owns its database and its QA ports. **Its OWN model
  database**, one per slot, never the shared one: a harness that
  clones `CREATE DATABASE … TEMPLATE` refuses the clone while any
  session holds the model open (`55006`), so one `psql` in another
  session reddens every slot at once. Measured 2026-09-22: one pack
  replayed its suite six times for this. Each slot exports its own
  `DATABASE_URL` on a database it created and migrated itself, and
  drops nobody else's — the repo's launch pack names its URL —
  migrated from the slot's own worktree before
  the gate: branches carry different migrations, so the model is
  rebuilt per run, never shared and never inherited. The slot's QA
  stack runs on a DIFFERENT database from its model: an `api` binary
  left connected to the model reddens the slot's own gates exactly
  like a foreign session would (measured 2026-09-22, one `ship` fell
  back to a throwaway database for it). Slot 0 is kept for the repair of `<default>`,
  which never waits for a slot.
- **Frontend app dirs** — where a user-visible file lives (`UI
  touched` at step 4); a lot touching one is a front lot; their ERE
  is the profile's `frontend` (`LOOP_FRONTEND` overrides).
- **Lint scope** — whether the repo's comply gate judges whole
  files or only added lines (`whole-file` | `added-lines`).
- **Template sections** — the five mandatory sections of
  `${CLAUDE_PLUGIN_ROOT}/skills/issue/SKILL.md` § Body template (`Category`,
  `Summary`, `Current behavior`, `Desired behavior`, `Acceptance
  criteria`), named in the project's language as /issue writes them
  (read off one recent issue body); English by default.
- **Generated paths** — generated types, lockfiles, `.sqlx/`,
  `openapi.json`: excluded from the line count; a type the diff
  declares that one of them holds is `Reinvented`.
- **QA launch pack** — per-slot values (model database URL, test
  clone pattern, merge command, report dir, dev sign-in), launch command + port override, readiness
  probe, the COMPLETE env block (every provider variable, every
  prompt id), DB-prepare path, the versioned seed recipe (the base
  every Breaker map composes on), the dependency probes of the login path
  (IdP, CORS preflight from a slot's console origin);
  `<main-repo>/.claude/skills/verify/` is authoritative when present. One stack per slot — its own ports
  and database — so two QAs never queue on each other. The values
  `skillhead slot` takes, each read off the launch pack: the disk
  threshold in GB (none named → 20, the one place this default
  lives), the test clone sweep command (none → `-`), the slot's env
  block (`KEY=value` lines, slot substituted), the schema-mismatch
  signal (an ERE on the gate's output) and its database recreation
  command, the stack's launch command and its ports per slot, the
  dependency probes as `<dependency>=<command>` (IdP, CORS, port,
  seed). A value the launch pack lacks is a launch pack line to add
  in the next lot (§ Rules); meanwhile its step runs without it.
- **Slot env hook** — the plugin's `hooks/hooks.json` registers
  `skillhead slot env` as a PreToolUse Bash hook: a command that
  names `…-worktrees/slot-<s>` (or `loop-<date>`), or runs from it, gets
  `<worktrees dir>/slot-<s>.env` (`loop-<date>.env`) sourced first (path written
  literally, `~/` or `$HOME/` admitted). The hook makes no permission
  decision: the rewritten command meets the session's own policy. No
  agent re-sources the slot's env; a slot command no path ties to its
  worktree is written `cd <worktree> && …`. `command -v skillhead`
  fails (the plugin is not enabled) → stop before any spawn, one line
  `🐢 skillhead plugin not enabled`.
- `git fetch origin <default>`; arm the watchdog (`RENDEZVOUS.md`)
  and run `skillhead loop_running start`:
  from then on AskUserQuestion is refused in this session (nobody
  answers an autonomous loop) until `skillhead loop_running stop`.
  A `state.md` with lots in flight → resume them at their phase
  before selecting anything, its `mode:`, `planned:` and `done:`
  kept, its `stopped:` line dropped; none, or no lot in flight → a
  new run (`integration:`/`integrated:` survive until the closing merges): `mode: run`, `planned: <N> (+0)`, N = the lots this run
  plans, `queue:` = the run's scope (step 1), no `done:` or `stopped:` line.

## The loop

**Before every spawn**, run `skillhead state
tick <state.md>`: it marks 🐢 every phase over its budget, then
reads the mode. Exit 2 `paused until <time>` → no spawn at all;
`draining` → phases of lots in flight only, no new lot; `drained` →
the closing when `state.md` holds `integrated:` lines (§ Closing), else
the loop stops like the disk stop below, `stopped: drained`. Exit 1
(an unreadable time) → one line `🐢 <its stderr>`, stop. The
pause ends by itself: past its time, the next tick passes and the
lots resume at their phase.

**Before every spawn** that opens a new lot (the `contract` phase of
a selected issue), also run `skillhead slot
disk <threshold> <worktrees dir> <sweep command|-> <n of
every lot in state.md>…`. It sweeps the test clones, then removes
the `issue-<n>` worktrees idle 20 h (never a lot in flight, never one
holding uncommitted work, branches kept), and exits 2 only when
still under the threshold. Exit 2 → no spawn, `held: contract #<n> —
<its stderr>` in `state.md`. A held spawn is retried first, before
any other, at the notification of the next lot that finishes (step
6). Exit 2 with no lot in flight → the loop stops: `stopped: disk —
<stderr>` in `state.md`, `skillhead loop_running stop`, CronDelete the
watchdog, one line `🐢 disk — <stderr> — free disk space, then
/loop-issues`. Phases of lots already in flight are never held.

1. **Select** — first replay Step 0's fresh-instructions test and
   `skillhead state fresh` (not `model`: the session's model is set); behind
   on a clean checkout → `git pull --ff-only`. An issue named in the invocation arguments is
   selected as is, whatever its labels, and the loop stops after its
   summary line. Else a split issue with unchecked tasks → next task,
   step 3. Else the pipeline of `origin/<default>` or the last
   `ci/release` e2e is red → its
   repair comes first: the open issue that names the failing job,
   else write its draft (job, first error lines) at
   `${CLAUDE_PLUGIN_ROOT}/skills/issue/SKILL.md` § Body template, spawn ONE
   `skillhead:issue-publisher` with the draft path, the label `needs-triage`
   (never `ready-for-agent`), the Step 0 forge facts and
   `${CLAUDE_PLUGIN_ROOT}/skills/issue/RECON.md` (§ Forge commands) → `CREATED
   <url>`, and select it; you never call the forge to create it. Else the
   next open issue of the run's scope, the `queue:` line of `state.md`,
   written at Step 0: the issues or the label (a lot, a `theme::`) the
   invocation names, plus the issues this loop creates. Nothing else:
   never the rest of `ready-for-agent`, never an issue created by
   someone else during the run (user, 2026-10-20). Order: one others
   name as `blocked by` first, then the one naming the most files, then
   lowest IID; one whose files a lot in flight touches only when
   nothing else remains. Scope drained → the closing. Draft mode: skip
   candidates with an MR from an `agent/issue-<n>` branch open or merged
   into `<integration>`, or on the skip list. Each queue candidate then runs, with
   `LOOP_INTEGRATED` = the issue numbers of the `integrated:` lines,
   `skillhead check issue <gh|glab>
   <project> <n> <Template sections…>`; exit 2 → `#<n> — <its
   stderr>` (`blocked by #N`, `outside template`) in the skip list of
   `state.md`, next candidate; exit 1 (forge unreadable) → stop the
   selection and report its stderr, nobody skipped. These lines are rewritten at every
   selection, except a step-3 `blocked by #<m>` line: it survives and
   skips its issue in both modes while #m is open (#m's state read as
   `skillhead check issue` reads a blocker). A closed or `integrated:` blocker frees its issue. None, no lot in a
   slot or `held:`, and `integrated:` lines → the closing (§ Closing);
   else end your turn, the watchdog re-polls.

2. **Lock** — write `<report-dir>/issue.md` (title, body, labels): every
   phase reads it, never the forge. Autonomous: `ready-for-agent` → `picked-by-agent`.
   Write the launch pack's env block, slot substituted, to
   `<worktrees dir>/slot-<s>.env` (beside the worktree, never in
   it): the slot env hook sources it.

3. **Build** — one spawn per phase (background), each with: the
   phase name, issue number (+ task `<k>`), `<main-repo>`, Step 0
   facts (generated clients included), report dir, the brief's path,
   and the files of the previous phases. End your turn after each
   spawn.
   - `skillhead:loop-builder` `contract` → `CONTRACTED <contract.md>` (or
     `NEEDS-CLARIFICATION <path>`; on an open dependency without MR
     → select that dependency next; on an undeclared dependency with
     an open MR (`Stack`) → draft mode stacks on it, autonomous puts the lot
     back to `ready-for-agent`, frees the slot and adds `#<n> —
     blocked by #<m>` to the skip list, kept until #m closes, step 1). The FIRST `CONTRACTED` is never
     the contract: `SendMessage` the SAME builder (still live, its
     context intact — never a new spawn) this message, always the
     same, exactly once per issue, and nothing about it earlier (the
     builder must not know it is coming; `BUILDER.md` says nothing
     of it):
     ```
     now come up with a much simpler solution that provides 80% of the benefits we are talking about here

     Rewrite contract.md in place: keep `Need`; redo `Shapes`, `Reuses`, `Tests`, `Slices` for that simpler solution. Add `## Simplification`, one line per thing dropped — what, and the property it costs; no acceptance criterion or constraint of the issue may be dropped. End with the same `CONTRACTED <contract.md>` line.
     ```
     → `CONTRACTED`. Then check `Shapes`, a closed `Tests` list,
     `Slices`, and run, in `<main-repo>`, `LOOP_BASE=origin/<integration>
     skillhead check contract <contract.md>`
     before either path below: exit 2 → `contract` once more, handed
     its stderr; a second exit 2 → step 5. No
     contract review, no `build 1` until it passes. Then `skillhead check
     overlap <contract.md> <contract.md of every other lot in a slot>`
     (`LOOP_GENERATED` = an ERE of Step 0's generated paths): exit 2
     NEVER holds a lot — `build 1` starts anyway, its prompt naming
     the lots in flight that share files (stderr) and asking for
     self-contained changes, no reformatting of existing code; the
     conflict is resolved at the pack's rebase or at the merge. A
     shared file costs one rebase, an idle slot costs a lot (user,
     2026-10-19: « shared files don't matter,
     there must always be 3 agents »). The lot always builds on
     `<integration>`.
     One slice under ~150 changed lines and no new table, route or
     dependency in `Shapes`, or a lot touching only tests, → `build 1`, no contract review: small
     issues ship in 30-60 min that way, where a contract review
     costs ~25 min for findings the code review catches as well. Else spawn ONE
     `skillhead:loop-contract-reviewer` with the contract path, its findings
     path, `CONTRACT-REVIEW.md`, `<main-repo>`.
   - contract reviewer, **one round, never two** → `CONTRACT-OK` →
     `build 1`, handed the review path (its `minor` lines amend the
     contract); `CONTRACT-REWORK <path>` → `contract` once more with
     that path (amends, answers each finding) → `skillhead check contract`
     and `overlap` again, as above → `build 1` whatever else that
     amendment says. The shipper copies the open findings into
     `pack-1.md` and the code review judges them on the diff.
     The first pass catches what a contract review is for — a defect
     already paid, a shape reinvented, a scope that fabricates work.
     Rounds beyond it argue prose: measured 2026-09-21 on one issue, four
     contract rounds and three reviews preceded a diff the code
     review passed `MERGEABLE` first try, and review 3 prescribed a
     migration order that was plainly wrong. A contract finding is
     cheap to carry into the code review; a round is not.
   - `skillhead:loop-builder` `build <k>` → `SLICED <k> <note>`. A `## Mechanic`
     section in the note → spawn ONE `skillhead:loop-mechanic` with it
     verbatim → `DONE <path>`. Then `build <k+1>` while slices
     remain, else `skillhead:loop-shipper` `pack`.
   - `skillhead:loop-shipper` `pack <r>` → `BLOCKED` on the test guard →
     `ship <r>` with that report, then `pack` again; a second →
     step 4 as flagged draft, never merged, even in automerge.
   - `skillhead:loop-shipper` `pack <r>` → `PACKED <pack-<r>.md>`. Spawn ONE
     `skillhead:loop-reviewer` with `r`, the pack path, its findings path
     `review-<r>.md`, `REVIEW.md` path, `<main-repo>`.
   - reviewer → `MERGEABLE`/`REWORK <path>`. Spawn `skillhead:loop-builder`
     `ship <r>` with the findings path and the verdict.
   - `skillhead:loop-builder` `ship <r>` → `SHIPPED <ship-<r>.md>`. `MERGEABLE`,
     `r = 3` or a `ship` that committed no code → `skillhead:loop-shipper`
     `deliver` with it (open findings ship flagged `[review not
     converged]`); else `pack <r+1>`.
   - `skillhead:loop-shipper` `deliver` → `DELIVERED <report>` → step 4 in the
     SAME turn, no spawn in between and no turn ended on it. Its
     Breaker map waits in `ship-<r>.md` for the closing (§ Closing).
     `BLOCKED <deliver.md>` (comply residue) → spawn `skillhead:loop-builder`
     `ship` once more with deliver.md, then `deliver` again; a second
     `BLOCKED` → step 4 as flagged draft. `FAILED <path>` → step 5.

4. **Verify** — from the report + forge only:
   - MR exists on `<base>`, draft in draft mode, title `(closes #<n>)`;
   - contract with `Shapes`, `Tests` and a `## Simplification`
     section (the 80 % pass ran); reviewer `Necessary`
     written, zero `Unpaid shape` left open; ship.md disposition
     table complete;
   - no comply finding on an added line. The forge pipeline does NOT
     gate the merge (user, 2026-09-22: "as long as it passes locally
     it's fine") — it runs the same trio, minutes to hours later, and
     waiting on it stalled finished work. Record its id, never block
     on it;
   - contract findings `applied` or `refuted — <evidence>`, ONE
     contract review; last
     review `MERGEABLE` with every finding `fixed`, `unpaid —
     <reason>` (its line under `## Unpaid findings` of the last
     `ship-<r>.md`) or `dropped — <evidence>`, or `[review not converged]` at round 3
     with the open findings as an MR comment;
   - `ship-<r>.md` holds a Breaker map, or `QA: not run — <reason>` —
     never on a front lot (Step 0);
   - description per `PRESENTATION.md` (read once).
   Non-conforming → SendMessage the shipper ONCE with the missing
   items; still non-conforming → step 5. Cap-hit review →
   confirm draft + findings comment, never merge, cleanup.
   Autonomous → the lot is `READY` and enters the merge queue below;
   once merged into `<integration>`, confirm the source branch
   removed and append `integrated: #<n> !<mr> <report-dir>` to
   `state.md`. The issue stays open, `picked-by-agent`, until the
   closing MR merges (only a merge into `<default>` closes it).
   Both modes, after the merge or the draft, and at step 5: clean up
   behind the issue — everything it created, nothing else.
   ```bash
   # QA stack first: a live session would refuse the drops below.
   skillhead slot qa-down <report-dir>/qa-stack.md
   wt=$(git -C ../<repo>-worktrees/slot-<s> rev-parse --show-toplevel)
   # The slot's worktree stays; only the lot leaves it.
   git -C "$wt" reset -q --hard && git -C "$wt" clean -fdq && git -C "$wt" switch -q --detach
   git branch -D agent/issue-<n> 2>/dev/null
   # The checkout's gates model, named as ci/check derives it (repo with GATES_DATABASE_URL only),
   # and its `_p…` clones: nothing reclaims them once the model is gone.
   [ -n "${GATES_DATABASE_URL:-}" ] && m="${GATES_DATABASE_URL##*/}_$(printf %s "$wt" | shasum -a 256 | cut -c1-12)" &&
     psql "${GATES_DATABASE_URL%/*}/postgres" -Atc "select format('DROP DATABASE IF EXISTS %I;', datname) from pg_database
       where datname = '$m' or datname ~ '^${m}_p[0-9]{10}_[0-9a-f]{12}\$'" | psql "${GATES_DATABASE_URL%/*}/postgres" -q
   git -C <main-repo> pull --ff-only origin <default>
   # Slot databases (launch pack: slot model URL, QA database named in qa-stack.md), AFTER step 1
   # ran for this slot: an issue selected → it reuses them, keep both; none → drop both, clones included.
   admin="${<slot-model-url>%/*}/postgres"; model="${<slot-model-url>##*/}"
   psql "$admin" -Atc "select format('DROP DATABASE IF EXISTS %I;', datname) from pg_database
     where datname in ('$model', '<qa-database>') or datname ~ '^${model}_p[0-9]{10}_[0-9a-f]{12}\$'" | psql "$admin" -q
   ```
   No target to prune: mbx prunes the managed targets itself. Every
   drop is a plain `DROP DATABASE`, never `WITH (FORCE)`: a refusal
   means another session still uses that database — leave it, one
   `🐢` line naming it. A database the issue did not create stays the
   user's, a worktree too outside `skillhead slot disk`'s prune. Close with
   `git worktree list` and the `pg_database` listing showing nothing
   of issue `<n>` left; what remains is named in the summary line.

   **Merge queue** (autonomous; draft mode only on "merge the drafts")
   — you hold it, FIFO, in `state.md`. A lot enters only once step 4
   is verified: verification happens before the merge task, never
   inside it. It leaves its slot for a `queued: #<n> !<mr> <sha> —
   <report dir>` line, and the slot selects the next issue: the merge
   runs in the integration worktree, never the slot's. The head is
   ONE `skillhead:loop-mechanic`, in `<worktrees dir>/loop-<date>` (created on
   first use, detached), with this closed task:
   1. The launch pack's merge command on the MR, foreground,
      `tail -40`, through `skillhead slot gate` when the launch pack names a
      schema signal: it merges `origin/<integration>` into the head,
      judges it, merges the MR pinned on that sha → `DONE <merged sha>`.
   2. A conflict where both sides only add lines (lists, tests,
      dashboard panels) → `git checkout --detach <head sha> && git
      merge origin/<integration>`, keep both sides, commit, push
      `HEAD:agent/issue-<n>`, step 1 again. Any other refusal →
      `BLOCKED` with it, no merge.
   A `BLOCKED` head leaves the queue and goes back to `ship` with
   the output. The next head's task is in flight before the relay
   line.

   **Registry and audit.** On `DONE`, run `skillhead state merged
   <report-root>/findings.md <n> <report-dir>`: each line of the lot's
   `## Unpaid findings` becomes `- [ ] #<n> <path:line> — <finding>
   — <reason>`, once, then `merged #<n>`. The registry sits beside
   `state.md`; `merged` only appends, the audit only ticks boxes and
   appends `audited`, which resets the merge count to zero.
   `audit due` → ONE `skillhead:loop-mechanic`: the audit of the `[ ]` entries
   only (the full suite runs at the closing). An entry whose finding is
   gone from `origin/<integration>` (judged on its content, the line
   drifts) → `[x] … — absent @<sha>`, never filed. An entry whose
   `<path:line> — <finding>` matches one already closed `— #<m>` →
   `[x] … — already #<m>`, never filed. The rest, grouped by related
   findings, become drafts per § Body template of
   `${CLAUDE_PLUGIN_ROOT}/skills/issue/SKILL.md` in
   `<report-root>/audit-<UTC date>/`; the mechanic ends `DONE
   <report-root>/audit-<UTC date>/`. Then you append `audited` to the
   registry and, per draft, spawn the `skillhead:issue-publisher`
   (`${CLAUDE_PLUGIN_ROOT}/skills/issue/SKILL.md` step 4) with the label
   `needs-triage`, never `ready-for-agent`. Only its `CREATED` (the
   forge returned the issue) marks the draft's entries
   `[x] … — #<m>`; a failed creation leaves them `[ ]` for the next
   audit.

5. **Failure** — never merge, close the MR if opened, comment the
   issue with the summary, run step 4's cleanup block (worktree,
   branch, QA stack, databases). NEEDS-CLARIFICATION:
   autonomous → both labels off + `agent-failed`; draft → skip list.
   Other: autonomous → `ready-for-agent` + `agent-failed`; draft →
   skip list.

6. **Relay** — at EVERY transition (phase to phase, verify to queue,
   one issue to the next), the next spawn is in flight BEFORE the
   summary line. No sub-orchestrator, no per-slot orchestrator: a
   child's notification never resumes a subagent (§ Agents). Summary
   lines:
   `✅ #<n> merged (!<mr>)` | `📝 #<n> drafted` |
   `⚠️ #<n> drafted flagged — <review|qa> not converged` | `❓ #<n>
   needs clarification` | `❌ #<n> failed → re-queued`. Writing #n's
   summary line retries a `held: contract` (disk) spawn before any
   other (§ The loop). The lot
   leaves its slot for a `done: #<n> <summary line>` line of
   `state.md`, suffixed ` rework` when a review of it returned
   `REWORK`; an issue added to the run raises the `(+k)` of
   `planned:`. Each summary line ends with the output of
   `skillhead state count <state.md>` (counter and rework rate), then
   the lines of the lot's `slowness.md`; every reply ends with that
   counter. Nothing else
   reaches the chat but 🐢 and a question: the rest goes to `<report-root>/to-know-<loop>.md`.
   A phase transition that ends no lot writes NOTHING in the chat —
   no recap of a report, no "slot 2 is building", no decision
   explained: the turn ends on the spawn. A reply is a summary line
   (with its counter), a 🐢, a 🔧, or the answer to the user's own
   question; anything longer goes to `a-savoir`. (User, 2026-10-15:
   « don't trickle out what happens outside the counter ».)

## Closing

The user's « close the loop » (in any language), or step 1 at the
end of the queue, sets `mode: drain`
and `closing: asked` in `state.md`. Once `tick` reads `drained`, the
closing holds slot 1 as lot `#closing` (`slot 1: #closing <phase>
<agent> since <time> — <report-root>/closing`), so `tick` reads
`draining` and lets its phases and its fix lots run:

1. ONE `skillhead:loop-shipper` `close` (SHIPPER.md) on
   `<worktrees dir>/loop-<date>`, handed the `integrated:` lines and
   the slot count N (the `slot k:` lines of `state.md`) →
   `QA-READY <qa-handoff.md>` (`ci/check` then the touched e2e specs
   ① ② green, SHIPPER.md § close; QA stack up), `DELIVERED`
   (no Breaker map: straight to 4) or `BLOCKED <close.md>` (each red with
   the lot whose merge first reddens it; a conflict with `<default>`
   → lot `#closing`, branch `agent/closing`, at step 3).
2. `QA-READY` → ONE `skillhead:loop-qa` with the handoff → verdict path →
   `skillhead:loop-shipper` `publish` with it.
3. Reds or a NO-GO → fix lots IN PARALLEL, one per group of specs
   (a Rust red: per crate; a NO-GO: per lot section), `#closing-fix-<k>`,
   each at `ship` in a free slot (as many as free slots, the rest
   wait; step 2's env file, BUILDER.md slice 1's worktree),
   branch `agent/closing-fix-<k>` from `origin/<integration>`,
   handed its rows of close.md or the verdict (tests: BUILDER.md § ship); each runs pack (test guard),
   review, deliver and the merge queue like any round. All merged → `close` again
   (a ② red: back to ②). Correctives at the closing
   are where tests get bent to go green (2026-10-15: one existing
   test re-seeded, +9 lines in an allowlist, unreviewed): no fix
   reaches `<integration>` outside that path. No cap on `close`
   passes: the closing runs until GO (user, 2026-10-21).
4. `publish` → `DELIVERED` with the MR `<integration>` → `<default>`
   (a NO-GO → `BLOCKED`, step 3).
   Autonomous → ONE `skillhead:loop-mechanic`: `skillhead merge_gate <closing
   report-dir> origin/<default> <head sha> <Frontend app dirs>`,
   then the certifying status green on that sha (`close` ran the
   script), then merge PINNED → issues closed by the forge; confirm
   each `integrated:` issue closed, then delete `<integration>`
   (remote branch, worktree, its gates model: step 4's drop with `wt` =
   that worktree) and the `integration:`/`integrated:`/
   `closing:` lines. Draft → the MR stays draft, the user merges.
   Summary line `🏁 <integration> → <default> (!<mr>), <k> lots`.

## Slowness is yours

Every stall of the loop is your defect to remove, never a fact to
report and wait out. A phase over its budget (§ Agents; `skillhead state
tick` marks it 🐢 in `state.md` and the lot's `slowness.md`), a
report naming an obstacle outside the diff (stuck process, taken
port, stale or locked database, cold or purged target, missing env
var, workaround flag, tool missing from PATH, red inherited from
`<default>`), or the same cause in two reports of any issue → it is
a **brake**: before the next phase spawn, remove it — a
`skillhead:loop-mechanic` with the exact command (kill, free the port, migrate
the slot's database, restore the env, drop the flag) when it is
environmental, an issue selected at slot 0 like a red `<default>`
when it is code — and write `brakes.md`: cause, action,
hours lost. A flaky test seen red in two reports is such a brake
whatever each report concluded: its repair jumps to slot 0, ahead of
the queue, never re-run until it passes. An agent that ends its turn
"waiting" on its own background gate is a brake too (RENDEZVOUS.md
§ Waiting). A brake you cannot remove (usage limit, a decision the
user owns: only money, a dropped criterion, an unspecified visible
behaviour, a production action — anything else is done, then
announced) is reported at once in one line `🐢 <cause> —
<what it costs per hour> — <the one action needed>`, never buried
in a relay line. Every brake handled is one line `🔧 <cause> →
<action>` in `to-know-<loop>.md`.

## Rules

- **Sequential by default: one agent in flight, ever.** One issue at
  a time, one phase spawn at a time, slot 1 only; the next spawn
  leaves only once the previous agent has reported. Parallel loops
  run only when the user asks for them in the invocation or the
  conversation ("in parallel", "N slots"), and then up to the
  number of slots they name. The user's own rule
  (2026-10-08, after three lots ran in parallel unasked): usage and
  disk are the binding constraints, and one agent at a time keeps
  both readable.
- When parallel was asked: each issue holds its slot, only on
  disjoint files, and every phase runs in parallel across slots,
  browser QA and `publish` captures included: each slot has its own
  console port (the launch pack's per-slot port) and each `skillhead:loop-qa`
  opens its own `new_page` with an `isolatedContext` named after its
  slot, passing that `pageId` to every chrome-devtools call — never
  `select_page`, never a page it did not open. Never queue a QA
  behind another slot's. A blocked lot runs every phase that does
  not need its blocker, then leaves its slot (step 3): the N slots
  asked are N agents in flight at all times, every relay fills an
  idle slot (user, 2026-10-15: « there must always be 3 agents at the
  same time » — two slots sat idle behind one held lot).
- A slot never waits on a file overlap: the N slots asked are N
  lots in flight while the queue holds a selectable issue. Only a
  declared `blocked by` (step 1) or the disk (§ The loop) keeps an
  issue out of a slot.
- Forge list calls narrowed on the first attempt (`per_page`,
  `labels`, `state`); an overflowing response is parsed from its
  persisted file.
- An open dependency MR never stops the loop. A declared one
  (`blocked by #<m>` in the body) is skipped at selection in both
  modes (step 1) until #m closes. Draft mode: an undeclared one
  found at contract stacks on it (step 3).
  Autonomous: never stacks; an undeclared one is waited for at
  selection too (`blocked by #<m>`, step 1) until it merges, then
  the lot builds on `<integration>`.
- Never push to the default branch; only the closing MR merges into
  it, never with the certifying gate (or the trio) red, on a sha it
  did not certify, or without QA GO. Into `<integration>`, only the
  merge queue head merges, after its check, and never a lot with
  comply beyond listed FPs, an unpaid shape or a review not
  converged. A pipeline pending or red does NOT hold a merge whose
  local gate is green. "Merge the drafts" covers only this session's MRs;
  a `[… not converged]` one, or another session's, is named back and needs its own yes.
- A fix to the repo's environment docs (the verify skill, a launch
  pack line) found during the loop never opens its own MR: agents
  read the main checkout's copy, so it travels in the next lot of
  that repo, listed under the MR's deviations.
- An inherited red — a gate red reproduced on `origin/<default>` —
  is not this loop's: `close` records it with the reproducing
  command. It still forbids the closing merge: the repair of
  `<default>` is selected first (step 1).
- **No phase of this loop ever opens an issue on the forge** (the
  red-pipeline issue of step 1 and the periodic audit's grouped drafts,
  § Merge queue, go through the /issue publisher, labelled
  `needs-triage`). The
  queue grew by 101 issues in three days because every phase filed
  its leftovers (user, 2026-09-24: "I thought you'd stopped
  creating them and folded them into the open MRs"). A finding
  that removes or corrects code is fixed in the MR; one that adds
  behaviour is paid in the MR when it lands in a file the lot
  already touches, and otherwise written as ONE line under
  `## Unpaid findings` in the phase report — never filed, never
  referenced as `Refs #`. The MR never grows in review beyond that.
  "Adds behaviour" is not the whole test — three findings are fixed in
  the MR whatever they look like: a duplication THIS MR posted (the
  second copy is the MR's own debt, never a successor's), any finding
  inside a function the MR already rewrote, and any finding under
  fifteen lines that opens no new file and settles no scope question.
  Measured 2026-09-23 on the fifteen issues one evening opened: nine
  fit their own MR, seven of them under fifteen lines without a new
  file, and three of the five invisible debts were duplications the
  MR itself had just posted. An issue is for work a successor must
  scope, not for a remedy already under the author's hand.
- The user's words set `mode:` in `state.md`: « drain », « finish the
  lots in flight » → `drain`; « pause until <time> » → `pause-until
  <time as UTC ISO-8601, date -u +%FT%TZ>`; « resume » → `run` (the
  same words in any language).
  `skillhead state tick` alone reads it.
- Only user interruption ends the loop, the summary line of an
  issue named in the invocation, or the disk, model and drained
  stops (§ The loop, Step 0); every way run
  `skillhead loop_running stop` first. The
  acknowledging reply ends with `💡 /reflect — mine this run for
  skill deltas`.
