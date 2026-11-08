# Security

## Reporting a vulnerability

Report privately through GitHub: the repository's **Security** tab →
**Report a vulnerability**. Please do not open a public issue for a way
around a guard; a private report gets a fix and a test before it is public.

## What the PreToolUse hooks are

skillhead's hooks (`hooks/hooks.json`) run before Claude Code executes a
tool call and may refuse it (exit 2). They are **guardrails for a
cooperative agent**: they stop an agent of the loop that, under time or
budget pressure, takes a shortcut its brief forbids — skipping git hooks,
running tests per lot, creating issues outside the reviewed `/issue` flow.
They also catch the same shortcut when it is suggested by text the agent
reads (an issue body, a README, a tool output).

They are **not a sandbox**. A determined adversary with shell access can
always run code they cannot see. Anything that must hold against a hostile
actor belongs in permissions (Claude Code's permission rules), in the forge
(branch protection, required status checks, CODEOWNERS) or in CI — never in
these hooks alone.

## What each hook protects

| Hook | Refuses | Scope |
|---|---|---|
| `refuse_hook_bypass` | A git call that skips git hooks: `--no-verify` (and its abbreviations), `git commit -n`, `core.hooksPath` set by `-c`, `--config-env`, `GIT_CONFIG_*` or `git config`, a git alias that does any of it (in the command or the repo's config), `HUSKY=0`, `HUSKY_SKIP_HOOKS`, `SKIP=…`, and any write, move, removal or mode change of a file in `.git/hooks/` | While a loop runs in the session, or for a `loop-*` agent |
| `builder_no_tests` | A test command, from the project profile's `test_patterns` | `loop-builder` only |
| `guard_issue_create` | An issue created on a guarded repo by anyone but `issue-publisher`: `gh`/`glab issue create`, `gh`/`glab api` writes to an issues endpoint, `curl`/`wget`/`http`/`xh` writes to a GitHub or GitLab issues endpoint, an MCP `*create_issue` tool | Repos in `guarded_repos` |
| `spawn_guard` | A phase prompt (or description) that names a gate command, from the profile's `gate_patterns` | Spawns of the guarded loop agents |
| `loop_running` | A question to the user (`AskUserQuestion`) while a loop runs unattended | The looping session |
| `slot env` | Nothing: it adds the slot's environment to commands that run in a slot's worktree | Bash calls naming a slot path |

## How commands are read

The command-parsing hooks never match patterns against raw text alone.
`skills/loop-issues/hooks/_shell.py` reads the command the way a shell
would, without running anything, and returns every simple command the text
would execute, including commands nested in:

- operators, subshells, `{ …; }`, `$( … )`, backticks, `<( … )`;
- `bash|sh|zsh -c`, `eval`, `cmd /c`, `pwsh -c` and `pwsh -EncodedCommand`;
- heredocs, here-strings and `echo`/`printf`/`cat` output fed to a shell;
- the string literals of `python|node|perl|ruby -c|-e` code;
- wrappers (`env`, `command`, `exec`, `sudo`, `nice`, `timeout`, `xargs`,
  `find -exec`, …);
- aliases and variables defined earlier in the same command text.

Quotes, backslash escapes and `$'…'` ANSI-C strings are resolved before
matching, so `git commit "--no-verify"` or `g\it commit -n` is read as
written to the shell, and a commit message or a grep pattern that merely
*mentions* `--no-verify` is not mistaken for the flag. Prompts are compared
after NFKC normalisation, with invisible characters removed and whitespace
collapsed.

`skills/loop-issues/hooks/test_bypass.py` holds the bypass corpora — each
way around a guard as a test that must be refused, next to look-alikes that
must pass — and a fuzz test that the parser never raises.

## Known limits

Static analysis cannot see what the command text does not contain. These
stay out of reach by design:

- **Code in files.** `bash ./script.sh`, `make x`, `npm run x`, a git alias
  defined in a global config file the repo's `git config` does not read, or
  a script written in one call and run in the next.
- **State from outside the text.** Variables, aliases and functions defined
  anywhere but the command being checked: a shell profile, a sourced file,
  an earlier tool call.
- **Computed or encoded payloads**, except `pwsh -EncodedCommand`:
  `$(echo Z2l0… | base64 -d)`, `printf '\x67it'`, string concatenation in an
  interpreter (`'gi' + 't'`), `IFS` tricks.
- **Indirect writes to `.git/hooks/`**: a path built at run time
  (`$(git rev-parse --git-path hooks)`), a symlink, or a tool not in the
  mutator list; a `core.hooksPath` that already points elsewhere.
- **Other channels.** A forge web UI, an API token used from a script file,
  a remote machine (`ssh host 'git commit -n'` is not inspected), an MCP
  tool whose name does not end in `create_issue`.
- **Prompt patterns are words, not intent.** `spawn_guard` matches gate
  command names; a paraphrase ("run the whole suite") passes.

## Failure behaviour

A hook that crashes exits 1, which Claude Code treats as **non-blocking**:
the tool call proceeds (fail-open). This keeps a parser bug from freezing
every agent, at the cost of a silent gap. To keep that gap closed, the
parser is fuzzed, every hook has tests, and `ci/check.py` runs them on
Linux, macOS and Windows. A hook that cannot read its input (no JSON, no
`agent_type`) passes the call: the scoping fields come from Claude Code,
which provides `agent_type` for subagent tool calls.

## Supported versions

Only the latest release of the plugin receives fixes.
