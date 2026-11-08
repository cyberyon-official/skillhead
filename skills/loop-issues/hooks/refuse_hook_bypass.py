#!/usr/bin/env python3
"""PreToolUse hook (Bash): refuse a git call that skips its hooks, inside a loop.

Acts while a loop-issues loop runs in the session, or for a loop agent;
elsewhere the plugin leaves git alone. Every command the text would run is
read by _shell.commands (nested shells, eval, wrappers, aliases, variables
assigned in the same text); SECURITY.md states what that cannot see.

Refused:
  - `--no-verify` (or an unambiguous prefix, `--no-veri…`) on any git
    subcommand, before `--`; `-n` in a `git commit` short-option cluster
  - core.hooksPath set through `-c`, `--config-env`, GIT_CONFIG_PARAMETERS,
    GIT_CONFIG_KEY_<n>, or `git config [set] core.hooksPath <value>`
  - a git alias (in the command or in the repo's config) that does any of it
  - the hook managers' skip switches: HUSKY=0, HUSKY_SKIP_HOOKS, SKIP=…
  - a command that writes, moves, removes or re-modes a file in .git/hooks/
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402
import _shell  # noqa: E402

MESSAGE = ("Refused: git hooks are never skipped (no --no-verify, no -n, no core.hooksPath "
           "rewrite, no hook-manager skip variable, no edit of .git/hooks). Pay the hook's "
           "findings in the commit. Rule: {why}.")

# `git commit` short options that take an argument: the rest of the cluster is it.
COMMIT_SHORT_WITH_ARG = set("mFcCt")
COMMIT_SHORT_OPTIONAL_ARG = set("uS")
COMMIT_LONG_WITH_ARG = {"--message", "--file", "--author", "--date", "--reuse-message", "--reedit-message",
                        "--fixup", "--squash", "--template", "--cleanup", "--trailer", "--pathspec-from-file"}
GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                       "--super-prefix", "--config-env", "--list-cmds", "--attr-source"}
MUTATORS = {"rm", "mv", "cp", "ln", "chmod", "chown", "truncate", "tee", "install", "unlink",
            "sed", "perl", "dd", "shred", "touch", "rsync", "del", "erase", "move", "copy",
            "remove-item", "set-content", "out-file", "move-item", "copy-item"}
HOOKS_DIR = re.compile(r"(^|[\\/])\.git[\\/]+hooks([\\/]|$)", re.I)


def is_hooks_path(key: str) -> bool:
    return key.strip().lower() == "core.hookspath"


def no_verify(arg: str) -> bool:
    return arg.startswith("--no-veri") and "--no-verify".startswith(arg)


def alias_bypasses(value: str) -> bool:
    """A git alias value that skips hooks: `commit -n`, `!git commit --no-verify`, …"""
    body = value[1:] if value.startswith("!") else "git " + value
    return any(git_reason(c) for c in _shell.commands(body) if c.name == "git")


def config_reason(key: str, value: str):
    if is_hooks_path(key):
        return "core.hooksPath is set"
    if key.lower().startswith("alias.") and alias_bypasses(value):
        return f"git alias {key[6:]} skips hooks"
    return None


def env_reason(env: dict):
    if env.get("HUSKY") == "0" or env.get("HUSKY_SKIP_HOOKS"):
        return "husky is switched off"
    if env.get("SKIP", "").strip():
        return "pre-commit hooks are skipped through SKIP"
    params = env.get("GIT_CONFIG_PARAMETERS", "")
    if re.search(r"core\.hookspath", params, re.I):
        return "core.hooksPath is set through GIT_CONFIG_PARAMETERS"
    for k, v in env.items():
        if re.fullmatch(r"GIT_CONFIG_KEY_\d+", k) and is_hooks_path(v):
            return "core.hooksPath is set through GIT_CONFIG_KEY_n"
    return None


def repo_alias(sub: str, cwd):
    """The repo's own alias for `sub`, when git knows one."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", sub):
        return None
    try:
        out = subprocess.run(["git", "config", "--get", f"alias.{sub}"], cwd=cwd or None,
                             capture_output=True, text=True, encoding="utf-8", timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def git_reason(cmd, cwd=None, depth=0):
    """Why this git invocation skips hooks, or None."""
    why = env_reason(cmd.env)
    if why:
        return why
    args, i = cmd.argv[1:], 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        if a == "-c" or a == "--config-env":
            kv = args[i + 1] if i + 1 < len(args) else ""
            i += 2
        elif a.startswith("-c") and len(a) > 2:
            kv, i = a[2:], i + 1
        elif a.startswith("--config-env="):
            kv, i = a[len("--config-env="):], i + 1
        else:
            i += 2 if a in GIT_GLOBAL_WITH_ARG else 1
            continue
        key, _, value = kv.partition("=")
        why = config_reason(key, value)
        if why:
            return why
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    if sub == "config":
        return config_command_reason(rest)
    options = rest[:rest.index("--")] if "--" in rest else rest
    verify = True
    skip_next = False
    for a in options:
        if skip_next:
            skip_next = False
            continue
        if no_verify(a):
            verify = False
        elif a == "--verify":
            verify = True
        elif sub == "commit" and a in COMMIT_LONG_WITH_ARG:
            skip_next = True
        elif sub == "commit" and re.fullmatch(r"-[A-Za-z]+", a):
            for k, ch in enumerate(a[1:]):
                if ch == "n":
                    verify = False
                if ch in COMMIT_SHORT_WITH_ARG:
                    skip_next = k == len(a) - 2      # `-m msg`: the next word is the message
                    break
                if ch in COMMIT_SHORT_OPTIONAL_ARG:
                    break                            # `-uno`, `-Skey`: the rest is the value
    if not verify:
        return f"git {sub} skips hooks"
    if depth < 3:
        alias = repo_alias(sub, cwd)
        if alias and alias_bypasses(alias):
            return f"git alias {sub} skips hooks"
    return None


def config_command_reason(rest):
    """`git config [set] core.hooksPath <value>` or an alias that skips hooks."""
    reading = {"--get", "--get-all", "--get-regexp", "-l", "--list", "--unset", "--unset-all",
               "get", "list", "unset", "--show-origin", "--edit", "-e", "edit"}
    if any(a in reading for a in rest) and not any(a in ("set", "--add", "--replace-all") for a in rest):
        return None
    positional, skip = [], False
    for a in rest:
        if skip:
            skip = False
            continue
        if a in ("-f", "--file", "--blob", "--type", "--default", "--comment", "--value"):
            skip = True
            continue
        if a.startswith("-") or a == "set":
            continue
        positional.append(a)
    if len(positional) >= 2:
        return config_reason(positional[0], " ".join(positional[1:]))
    return None


def hooks_dir_reason(cmd):
    """A command that changes a file in .git/hooks/."""
    if cmd.name == "git":
        return None
    writes = [t for op, t in cmd.redirects if ">" in op]
    if any(HOOKS_DIR.search(t) for t in writes):
        return "a file in .git/hooks/ is overwritten"
    if cmd.name in MUTATORS and any(HOOKS_DIR.search(a) for a in cmd.argv[1:]):
        if cmd.name == "sed" and not any(a.startswith("-i") or a == "--in-place" for a in cmd.argv[1:]):
            return None
        return "a file in .git/hooks/ is changed"
    return None


def reason(command: str, cwd=None):
    for cmd in _shell.commands(command):
        why = git_reason(cmd, cwd) if cmd.name == "git" else hooks_dir_reason(cmd) or (
            env_reason(cmd.env) if cmd.name == "pre-commit" else None)
        if why:
            return why
    return None


def refused(command: str, cwd=None) -> bool:
    return reason(command, cwd) is not None


def main(argv):
    data = L.hook_input()
    in_loop = L.loop_running(data.get("session_id")) or L.bare_agent(data.get("agent_type")).startswith("loop-")
    if not in_loop:
        return 0
    cwd = data.get("cwd") if data.get("cwd") and os.path.isdir(str(data.get("cwd"))) else None
    why = reason(str(L.tool_input(data).get("command") or ""), cwd)
    if why:
        raise L.Refuse(MESSAGE.format(why=why))
    return 0


if __name__ == "__main__":
    L.run(main)
