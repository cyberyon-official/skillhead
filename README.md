<p align="center">
  <img src="logo.png" alt="skillhead logo: a skull wearing a spiked helmet marked SKILL" width="220">
</p>

<h1 align="center">skillhead</h1>

Claude Code skills that take a need from a loose description to a merged
change, with review, QA and a single MR to the default branch — and a
project template that gives any repo the structure those skills read.

Every script is standard-library Python and runs on Linux, macOS and
Windows.

## Credits

skillhead is built on [Romain Baumier](https://github.com/rbaumier)'s
[`rbaumier/skills`](https://github.com/rbaumier/skills). The `/issue` and
`/loop-issues` workflows — the contract reviewed before any code, the
review loop, the integration branch, the QA gate — are his design, as is
the "one rule, one place" project structure the template follows.
skillhead keeps those two workflows and the skills they load, and makes
them portable: stdlib Python hooks, a per-project profile instead of a
hard-wired stack, a Claude Code plugin. Thanks, Romain.

## Install

skillhead is a Claude Code plugin; this repository is also its marketplace.

```
/plugin install skillhead --marketplace cyberyon-official/skillhead
```

On Claude Code before 2.1.275, in two steps:

```
/plugin marketplace add cyberyon-official/skillhead
/plugin install skillhead@skillhead
```

Optional: `claude plugin configure skillhead` sets `guarded_repos`, the
`owner/repo` list where only the `/skillhead:issue` publisher may create
issues.

Requirements: Claude Code, `git`, Python ≥ 3.10, `gh` or `glab`. On
Windows, Git for Windows — Claude Code runs hooks and its Bash tool under
Git Bash.

## What's inside

| Skill | What it does |
|---|---|
| `/skillhead:issue` | Turns a need described in bulk into one minimal, need-only issue on GitHub or GitLab. An agent checks it does not exist yet; a scoper writes it, a reviewer judges it (3 rounds max); the human settles implicit decisions; only the publisher agent creates it (hook-enforced). |
| `/skillhead:loop-issues` | Implements issues autonomously, each phase in a fresh agent: a contract reviewed before any code, build, diff review (3 rounds max), merge into the run's integration branch; at the closing, full gates and QA, then one MR to the default branch. |
| `ponytail`, `ponytail-review` | What to cut: speculative abstractions, reinvented stdlib, needless dependencies. Loaded by the builder and the reviewer. |
| `quality-bar`, `quality-bar-review` | The author-side and reviewer-side quality checklists. |
| `qa` | The QA executor's method: drive the real app, spawn Breakers on hostile inputs, return GO / NO-GO. |

| Path | Content |
|---|---|
| `.claude-plugin/` | `plugin.json` (manifest), `marketplace.json`, `icon.png` |
| `skills/<name>/` | The seven skills; `skills/loop-issues/hooks/` holds the hook scripts |
| `agents/` | The ten pinned agents, invoked as `skillhead:<name>` |
| `hooks/hooks.json` | The plugin's PreToolUse hooks |
| `bin/skillhead` | Runs a plugin script with a real Python 3.10+; on the Bash tool's `PATH` while the plugin is enabled (`skillhead state tick <state.md>`) |

`CONTEXT.md` defines the vocabulary the skills share (roles, contract, gates).

## Start a project

In Claude Code, from the project's directory:

```
/skillhead:initialize
```

It infers the name, forge and default branch from the repository, previews
what it will write, never overwrites a file, fills `ci/gates.json` and the
toolchain guide for the detected stack, runs the merge gate, and leaves the
commit to you.

Without Claude, the generator alone does the first step:

```sh
python3 new_project.py ../my-project --name "My project" --forge github --mode draft
python3 new_project.py ../existing-project --dry-run   # lists what it would write
```

This lays down the structure the skills read — `CLAUDE.md` as a pointer
table, coding guides, vocabulary, ADRs, review checklist, test rules,
launch pack, hook profile — plus a merge gate (`ci/check.py`) with guards
that keep those docs honest. Nothing assumes a stack. Details:
[`templates/README.md`](templates/README.md).

## Adapt the hooks to a project

The hooks know no stack. They read `<repo>/.claude/loop-issues.json` (or
the file named by `LOOP_PROFILE`), else generic defaults covering cargo,
npm/pnpm/yarn/bun, pytest, go, maven/gradle, dotnet, make/just, rspec,
phpunit, mix and swift.

| Key | Read by | Meaning |
|---|---|---|
| `test_patterns` | `builder_no_tests.py` | Regexes of the test commands a builder may not run. |
| `test_allowed`, `test_allowed_hint` | `builder_no_tests.py` | Replays allowed anyway (named group `keep` is preserved). |
| `gate_patterns` | `spawn_guard.py` | Regexes of the gates a phase prompt may not name. |
| `guarded_agents` | `spawn_guard.py` | Agent types the spawn guard applies to. |
| `frontend` | `check.py contract` | Regex of frontend paths: a front lot owes an e2e test per need. `LOOP_FRONTEND` overrides. |
| `generated` | `check.py overlap` | Regex of generated paths, which never hold a lot. `LOOP_GENERATED` overrides. |
| `toolchain_notes` | orchestrator, every agent | A markdown file of the repo with the toolchain's rules (build cache, artefact repair, banned commands). |

A `<key>_extra` key appends to the default list instead of replacing it.
Examples: `skills/loop-issues/profiles/generic.json` and
`skills/loop-issues/profiles/rust-pnpm-monorepo.{json,md}`.

## Contributing

This repo follows its own template: start from `CLAUDE.md`, which points
to the guides, decisions and checklists (some still to fill in).

```sh
python3 ci/check.py   # merge gate: hook tests, template tests, then the guards
```

CI (`.github/workflows/hooks.yml`) runs it on Ubuntu, macOS and Windows
with Python 3.10 and 3.13, and rejects any path that is invalid on NTFS.

## Security

The hooks are guardrails for a cooperative agent, not a sandbox: what they
refuse, how they read commands and what they cannot see is in
[`SECURITY.md`](SECURITY.md).

## Licence

MIT — see `LICENSE`. Derived from [`rbaumier/skills`](https://github.com/rbaumier/skills)
(MIT, Romain Baumier); third-party parts are listed in `THIRD_PARTY.md`.
