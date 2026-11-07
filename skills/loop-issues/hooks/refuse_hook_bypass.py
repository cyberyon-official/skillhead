#!/usr/bin/env python3
"""PreToolUse hook (Bash): refuse a git call skipping pre-commit.

Heredoc bodies and quoted strings may cite the flags: they are dropped.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

HEREDOC = re.compile(r"""(^|[^<])<<-?\s*["']?[A-Za-z0-9_]+""")
GIT = r"(^|[^A-Za-z0-9_.-])git(\s+(-[cC]\s*\S+|--\S+))*\s+"
# -n counts only after commit's argument-less short flags: -uno, -amn pass.
NO_VERIFY = re.compile(GIT + r"commit(\s[^;&|]*)?\s(--no-verify|-[apseiovqz]*n)")
HOOKS_PATH = re.compile(
    GIT + r"-c\s*core\.hookspath=|"
    + GIT + r"config(\s+(--global|--local|--system|--worktree|set))*\s+core\.hookspath\s+[^\s-]",
    re.IGNORECASE,
)
MESSAGE = ("Refused: the pre-commit hook is never skipped (no --no-verify, no -n, "
           "no core.hooksPath rewrite). Pay its findings in the commit.")


def strip_heredocs(command: str) -> str:
    """The command without closed heredoc bodies; an unclosed one is kept."""
    out, end, body = [], "", ""
    for line in command.split("\n"):
        if end:
            if re.fullmatch(r"\s*" + re.escape(end) + r"\s*", line):
                end = body = ""
            else:
                body += line + "\n"
            continue
        out.append(line + "\n")
        m = HEREDOC.search(line)
        if m:
            end = re.sub(r"""^.*<<-?\s*["']?""", "", m.group(0))
    return "".join(out) + body  # a body never closed was no heredoc: checked


def flatten(command: str) -> str:
    text = strip_heredocs(command).replace("\n", ";")
    text = text.replace("\\;", " ")
    return re.sub(r"""'[^']*'|"[^"]*\"""", "Q", text)


def refused(command: str) -> bool:
    text = flatten(command)
    return bool(NO_VERIFY.search(text) or HOOKS_PATH.search(text))


def main(argv):
    if refused(L.tool_input(L.hook_input()).get("command") or ""):
        raise L.Refuse(MESSAGE)


if __name__ == "__main__":
    L.run(main)
