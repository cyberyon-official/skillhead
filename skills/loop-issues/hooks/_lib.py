"""Shared helpers of the loop-issues hooks — stdlib only, Linux/macOS/Windows.

Exit-code contract of every hook script:
  0  pass
  1  usage, forge or unreadable-input error — never a refusal
  2  refused, the reason on stderr (Claude Code reads exit 2 as a block)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

sys.dont_write_bytecode = True  # a __pycache__ in the skill would trip `state fresh`

HOOKS_DIR = Path(__file__).resolve().parent
SKILL_DIR = HOOKS_DIR.parent
PROFILE_NAME = "loop-issues.json"  # read from <repo>/.claude/


class Refuse(Exception):
    """Exit 2: the hook refuses; the message goes to stderr."""


class Fail(Exception):
    """Exit 1: usage or environment error, never a refusal."""


def run(main: Callable[[list], Optional[int]]) -> None:
    """Runs `main(argv)` and maps Refuse/Fail to the exit-code contract."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
        except (AttributeError, ValueError):
            pass
    try:
        code = main(sys.argv[1:]) or 0
    except Refuse as e:
        print(str(e), file=sys.stderr)
        code = 2
    except Fail as e:
        if str(e):
            print(str(e), file=sys.stderr)
        code = 1
    sys.stdout.flush()
    sys.exit(code)


# ---------------------------------------------------------------- I/O

def read_stdin() -> str:
    data = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read()
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def hook_input() -> dict:
    """The JSON a Claude Code hook gets on stdin; {} when empty or invalid."""
    raw = read_stdin().strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def tool_input(data: dict) -> dict:
    value = data.get("tool_input")
    return value if isinstance(value, dict) else {}


def read_text(path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def append_line(path, line: str) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def lines(path) -> list:
    return read_text(path).splitlines()


def claude_home() -> Path:
    return Path.home() / ".claude"


def run_dir() -> Path:
    return claude_home() / "run" / "loop-issues"


def session_id() -> str:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not sid:
        raise Fail("CLAUDE_CODE_SESSION_ID: parameter null or not set")
    return sid


# ---------------------------------------------------------------- time

def parse_iso(text: str) -> datetime:
    """ISO 8601 (`2026-10-15T08:00:00Z`) → aware UTC datetime; Fail when unreadable."""
    t = text.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        value = datetime.fromisoformat(t)
    except ValueError:
        raise Fail(f"unreadable time: {text}")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- shell

def shell_argv(command: str) -> list:
    """The argv that runs a launch-pack command, which is written in POSIX sh.

    LOOP_SHELL overrides. On Windows, Git Bash (next to git) is preferred —
    never the WSL launcher in System32; without any bash, cmd.exe runs it.
    """
    override = os.environ.get("LOOP_SHELL")
    if override:
        return [override, "-c", command]
    bash = None
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            for root in list(Path(git).resolve().parents)[:3]:  # Git\cmd, Git\bin, Git\mingw64\bin
                for candidate in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
                    if candidate.exists():
                        bash = str(candidate)
                        break
                if bash:
                    break
        if bash is None:
            found = shutil.which("bash")
            if found and "system32" not in found.lower():
                bash = found
    else:
        bash = shutil.which("bash") or shutil.which("sh")
    if bash:
        return [bash, "-c", command]
    return [os.environ.get("COMSPEC", "cmd.exe"), "/c", command]


def sh(command: str, **kwargs) -> subprocess.CompletedProcess:
    argv = shell_argv(command)
    if argv[0] == os.environ.get("COMSPEC", "cmd.exe"):
        return subprocess.run(command, shell=True, **kwargs)  # let Python quote for cmd.exe
    return subprocess.run(argv, **kwargs)


def git(*args, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- markdown

def section(text: str, name: str) -> list:
    """Lines of section `## name` (exact heading) up to the next `## `."""
    out, inside = [], False
    for line in text.splitlines():
        if line == f"## {name}":
            inside = True
            continue
        if line.startswith("## "):
            inside = False
        if inside:
            out.append(line)
    return out


def backticked(line: str) -> list:
    return re.findall(r"`([^`]*)`", line)


# ---------------------------------------------------------------- profile

# Commands that run tests. Generic across ecosystems; a project narrows or
# widens them in <repo>/.claude/loop-issues.json (`test_patterns`).
DEFAULT_TEST_PATTERNS = [
    r"\bcargo +(test|t)(?!\w)",
    r"\bnextest +(run|r)(?!\w)",
    r"\b(npm|pnpm|yarn|bun)( +(-C|--dir|--filter|--prefix) +\S+)* +(run +)?test(?![\w:-])",
    r"\b(vitest|jest|playwright|mocha|ava|cypress)\b",
    r"\b(pytest|tox|nox)\b",
    r"\bpython[0-9.]* +-m +(pytest|unittest)\b",
    r"\bgo +test\b",
    r"\b(mvnw?|gradlew?)\b[^;&|]*\b(test|verify)\b",
    r"\bdotnet +test\b",
    r"\b(make|just|task) +(test|check)\b",
    r"\b(ctest|rspec|phpunit)\b",
    r"\bmix +test\b",
    r"\bswift +test\b",
    r"\bslot\.py +gate\b",
]

# Commands a phase prompt must not name: the brief owns each phase's gates.
DEFAULT_GATE_PATTERNS = DEFAULT_TEST_PATTERNS[:-1] + [
    r"\bcargo +(check|clippy)\b",
    r"\bclippy\b",
    r"\b(npm|pnpm|yarn|bun)( +(-C|--dir|--filter|--prefix) +\S+)* +(run +)?(check|lint|typecheck)(?![\w-])",
    r"\b(eslint|biome|tsc|ruff|mypy|pyright|golangci-lint)\b",
    r"\bgo +vet\b",
]

DEFAULT_PROFILE = {
    "test_patterns": DEFAULT_TEST_PATTERNS,
    "test_allowed": [],
    "gate_patterns": DEFAULT_GATE_PATTERNS,
    "guarded_agents": ["loop-builder", "loop-shipper", "loop-reviewer", "loop-contract-reviewer"],
    "frontend": "",
    "generated": "",
}


def repo_root(cwd=None) -> Optional[Path]:
    result = git("rev-parse", "--show-toplevel", cwd=cwd or None)
    return Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None


def load_profile(cwd=None) -> dict:
    """DEFAULT_PROFILE overlaid by LOOP_PROFILE (a path) or <repo>/.claude/loop-issues.json."""
    profile = dict(DEFAULT_PROFILE)
    path = os.environ.get("LOOP_PROFILE")
    if not path:
        root = repo_root(cwd if cwd and Path(cwd).is_dir() else None)
        if root and (root / ".claude" / PROFILE_NAME).is_file():
            path = str(root / ".claude" / PROFILE_NAME)
    if path:
        try:
            data = json.loads(read_text(path))
        except (OSError, ValueError) as e:
            raise Fail(f"profile {path}: {e}")
        for key, value in data.items():
            if key.endswith("_extra") and key[:-6] in profile:
                profile[key[:-6]] = list(profile[key[:-6]]) + list(value)
            elif not key.startswith("$") and not key.startswith("_"):
                profile[key] = value
    return profile


def first_match(patterns: Iterable[str], text: str) -> Optional[str]:
    """The leftmost match of any pattern in text (grep -o | head -1)."""
    best = None
    for pattern in patterns:
        m = re.search(pattern, text)
        if m and (best is None or m.start() < best.start()):
            best = m
    return best.group(0) if best else None
