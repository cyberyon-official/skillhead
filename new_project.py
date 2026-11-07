#!/usr/bin/env python3
"""Lays down the agent-ready structure of templates/project/ in a directory.

  python3 new_project.py <dir> [--name NAME] [--forge github|gitlab]
                         [--mode draft|automerge] [--default-branch main]
                         [--no-git]

<dir> absent or empty → a new project (git init on --default-branch).
<dir> holding files → the structure is added beside them: an existing
file is never overwritten, it is listed so you merge it by hand.
Stack-agnostic: fill ci/gates.json, docs/agents/toolchain.md and
.claude/skills/verify/SKILL.md for the project's stack afterwards.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TEMPLATE = Path(__file__).resolve().parent / "templates" / "project"
FORGE_CI = {"github": ".github/workflows/ci.yml", "gitlab": ".gitlab-ci.yml"}


def render(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--name")
    ap.add_argument("--forge", choices=sorted(FORGE_CI), default="github")
    ap.add_argument("--mode", choices=["draft", "automerge"], default="draft")
    ap.add_argument("--default-branch", default="main")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args(argv)

    target = Path(a.dir).expanduser().resolve()
    fresh = not target.exists() or not any(target.iterdir())
    values = {"PROJECT": a.name or target.name, "FORGE": a.forge, "MODE": a.mode,
              "DEFAULT_BRANCH": a.default_branch}
    skip = {path for forge, path in FORGE_CI.items() if forge != a.forge}

    written, kept = [], []
    for src in sorted(TEMPLATE.rglob("*")):
        relative = src.relative_to(TEMPLATE).as_posix()
        if src.is_dir() or relative in skip or "__pycache__" in src.parts:
            continue
        dst = target / relative
        if dst.exists():
            kept.append(relative)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(src, dst)
        else:
            dst.write_bytes(render(text, values).encode("utf-8"))
        written.append(relative)

    if fresh and not a.no_git and shutil.which("git") and not (target / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", a.default_branch, str(target)], check=False)

    print(f"{len(written)} files written to {target}")
    if kept:
        print("Already present, left untouched (merge by hand):")
        for relative in kept:
            print(f"  {relative}")
    print("Next: fill in ci/gates.json, docs/agents/toolchain.md, .claude/skills/verify/SKILL.md,"
          " CONTEXT.md, PRODUCT.md; then run `python3 ci/check.py`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
