#!/usr/bin/env python3
"""Installs the skills of this repo into a Claude Code config dir — any OS.

  python3 install.py [--target ~/.claude] [--python CMD] [--guard-repos owner/repo …] [--dry-run]

- copies every skill directory (skills/<name>/ holding SKILL.md) to <target>/skills/
- copies the pinned agents (skills/*/agents/*.md) to <target>/agents/
- registers in <target>/settings.json, idempotently:
    PreToolUse Bash  → loop-issues/hooks/slot.py env      (required by /loop-issues)
    PreToolUse Bash + mcp create_issue → issue/hooks/guard_issue_create.py <repos>
                                                           (only with --guard-repos)
- writes the interpreter into the installed hook commands: `python3` stays
  when it is on PATH, else this interpreter's absolute path (Windows ships
  `python`/`py`, not `python3`). --python forces one.

Copies, never symlinks: symlinks need admin rights on NTFS.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def interpreter(forced):
    if forced:
        return forced
    if shutil.which("python3"):
        return "python3"
    return '"' + Path(sys.executable).as_posix() + '"'


def rewrite_python(text, py):
    if py == "python3":
        return text
    return re.sub(r"\bpython3(?= +[\"']?(~|\$HOME)/\.claude/skills/)", lambda _: py, text)


def hook_command(py, target, script, *args):
    path = (target / "skills" / script).as_posix()
    return " ".join([py, f'"{path}"', *args])


def add_hook(settings, matcher, command):
    entries = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
    for entry in entries:
        if entry.get("matcher") == matcher:
            hooks = entry.setdefault("hooks", [])
            if any(h.get("command") == command for h in hooks):
                return False
            hooks.append({"type": "command", "command": command})
            return True
    entries.append({"matcher": matcher, "hooks": [{"type": "command", "command": command}]})
    return True


def drop_hooks(settings, needle):
    """Removes earlier registrations of a script (an old path or interpreter)."""
    for entry in settings.get("hooks", {}).get("PreToolUse", []):
        entry["hooks"] = [h for h in entry.get("hooks", []) if needle not in h.get("command", "")]


def main():
    for stream in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default=str(Path.home() / ".claude"))
    ap.add_argument("--python", help="interpreter command written into hook commands")
    ap.add_argument("--guard-repos", nargs="*", default=[], metavar="OWNER/REPO")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    target, py, dry = Path(a.target).expanduser(), interpreter(a.python), a.dry_run

    skills = sorted(p.parent for p in REPO.glob("skills/*/SKILL.md"))
    for src in skills:
        dst = target / "skills" / src.name
        print(f"skill  {src.name} → {dst}")
        if dry:
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=IGNORE)
        for md in dst.rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            new = rewrite_python(text, py)
            if new != text:
                md.write_bytes(new.encode("utf-8"))

    agents = target / "agents"
    for src in sorted(REPO.glob("skills/*/agents/*.md")):
        print(f"agent  {src.name} → {agents / src.name}")
        if not dry:
            agents.mkdir(parents=True, exist_ok=True)
            text = rewrite_python(src.read_text(encoding="utf-8"), py)
            (agents / src.name).write_bytes(text.encode("utf-8"))

    settings_path = target / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    drop_hooks(settings, "loop-issues/hooks/slot.")
    add_hook(settings, "Bash", hook_command(py, target, "loop-issues/hooks/slot.py", "env"))
    drop_hooks(settings, "guard-issue-create")
    drop_hooks(settings, "guard_issue_create")
    if a.guard_repos:
        guard = hook_command(py, target, "issue/hooks/guard_issue_create.py", *a.guard_repos)
        add_hook(settings, "Bash", guard)
        add_hook(settings, "mcp__.*create_issue", guard)
    settings["hooks"]["PreToolUse"] = [e for e in settings["hooks"]["PreToolUse"] if e.get("hooks")]
    print(f"hooks  → {settings_path} (interpreter: {py})")
    if dry:
        print(json.dumps(settings.get("hooks"), indent=2))
    else:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_bytes((json.dumps(settings, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print("Done. Per target repo: add .claude/loop-issues.json (see skills/loop-issues/profiles/).")


if __name__ == "__main__":
    main()
