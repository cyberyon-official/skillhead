---
name: initialize
description: >-
  Lay down the skillhead project structure (pointer CLAUDE.md, guides, ADRs,
  launch pack, hook profile, merge gate) in a new or existing repository, then
  fill the merge gate for its stack. Use when the user asks to initialize,
  bootstrap or set up a project for skillhead.
argument-hint: "[dir] [--name NAME] [--forge github|gitlab] [--mode draft|automerge] [--default-branch BRANCH]"
disable-model-invocation: true
---

# /skillhead:initialize

`new_project.py` is the only thing that writes the template; this skill runs
it with the right facts and fills in what a script cannot guess. It never
overwrites a file and never commits.

## 1. Gather the facts

Target: the `dir` argument, else the current working directory. For each
fact the user did not pass, infer it and show where it came from:

| Fact | Source, in order |
|---|---|
| `--name` | `name` in `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` module tail; else the directory name |
| `--forge` | `git remote get-url origin`: `github` if it contains `github`, `gitlab` if it contains `gitlab`; else ask |
| `--default-branch` | `git symbolic-ref --short refs/remotes/origin/HEAD` minus `origin/`; else the current branch; else `main` |
| `--mode` | `draft` — `automerge` only when the user asks for it |

## 2. Preview, then write

1. Run `skillhead new_project <dir> <flags> --dry-run` and show the user the
   files it would write and the ones it keeps.
2. On their go-ahead, run the same command without `--dry-run`.
3. For each kept file, compare it with `templates/project/` in the plugin and
   propose the missing parts as an edit the user approves. A kept
   `CLAUDE.md` gets the pointer table merged in, never replaced.

## 3. Fill the gate for the stack

Detect the stack from its manifests (`package.json` and its lockfile,
`pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml` / `build.gradle*`,
`*.csproj` / `*.sln`, `Makefile`), and the CI the repo already runs. Then:

- **`ci/gates.json`**: set the `check`, `lint`, `test` and `build` steps to
  commands the project already uses (its scripts, Makefile targets, existing
  CI jobs). Leave a step's `run` empty rather than invent a command; remove a
  step only if the stack has no such phase.
- **`docs/agents/toolchain.md`**: replace each `<…>` placeholder with the
  stack's package manager, lockfile, cache repair command and banned commands.
- **`.claude/loop-issues.json`**: add the stack's test runners to
  `test_patterns_extra` when the defaults miss them.

Run each gate command once before writing it in. One that fails is reported
to the user, not written.

## 4. Check and hand over

Run `python3 ci/check.py` in the target (`python` or `py -3` on Windows) and
report its result. Then list what only the user can write, each with one
line on what it holds:

- `CONTEXT.md` — the domain vocabulary;
- `PRODUCT.md` — users, needs, product rules;
- `DESIGN.md` — the visual and interaction design, if there is a UI;
- `.claude/skills/verify/SKILL.md` — how to launch and drive the app.

Stop there. The user reviews and commits.
