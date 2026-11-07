#!/usr/bin/env python3
"""Merge gate: the steps of ci/gates.json, then the guards of ci/guards/.

  python3 ci/check.py            every step, then the guards
  python3 ci/check.py --guards   guards only
  python3 ci/check.py --list     print the steps and exit

Exit 0 when everything is green, 1 otherwise. Stdlib only: Linux, macOS,
Windows. Steps are POSIX shell commands, run under bash (Git Bash on
Windows); a step with an empty `run` is skipped and said so. `{python}`
in a step stands for the interpreter running this script.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
CI = Path(__file__).resolve().parent
ROOT = CI.parent


def shell_argv(command):
    override = os.environ.get("CHECK_SHELL")
    if override:
        return [override, "-c", command]
    if os.name == "nt":
        bash = git_bash()
        return [bash, "-c", command] if bash else None  # None: cmd.exe, via shell=True
    return [shutil.which("bash") or "/bin/sh", "-c", command]


def git_bash():
    """Git for Windows' bash.exe, never the WSL launcher in System32."""
    git = shutil.which("git")
    if git:
        for root in list(Path(git).resolve().parents)[:3]:
            for bash in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"):
                if bash.exists():
                    return str(bash)
    found = shutil.which("bash")
    return found if found and "system32" not in found.lower() else None


def load_steps(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    steps = data.get("steps", [])
    for step in steps:
        if not isinstance(step, dict) or not step.get("name"):
            raise SystemExit(f"{path}: every step needs a name")
    return steps


def run_steps(steps, cwd=ROOT, out=sys.stdout):
    """Runs each step; returns the names of the red ones."""
    red = []
    for step in steps:
        name, command = step["name"], (step.get("run") or "").strip()
        command = command.replace("{python}", '"' + Path(sys.executable).as_posix() + '"')
        if not command:
            print(f"· {name}: no command in ci/gates.json, skipped", file=out)
            continue
        start = time.monotonic()
        argv = shell_argv(command)
        result = subprocess.run(argv if argv else command, shell=argv is None, cwd=cwd,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        took = time.monotonic() - start
        if result.returncode == 0:
            print(f"✓ {name} ({took:.0f} s)", file=out)
            continue
        red.append(name)
        tail = result.stdout.decode("utf-8", "replace").splitlines()[-40:]
        print(f"✗ {name} (exit {result.returncode}, {took:.0f} s): {command}", file=out)
        for line in tail:
            print(f"    {line}", file=out)
    return red


def run_guards(verbosity=1):
    suite = unittest.defaultTestLoader.discover(str(CI / "guards"), pattern="test_*.py",
                                                top_level_dir=str(CI / "guards"))
    result = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout).run(suite)
    return result.wasSuccessful()


def main(argv):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    steps = load_steps(CI / "gates.json")
    if "--list" in argv:
        for step in steps:
            print(f"{step['name']}: {step.get('run') or '(empty)'}")
        return 0
    red = [] if "--guards" in argv else run_steps(steps)
    print("— guards (ci/guards)")
    if not run_guards():
        red.append("guards")
    if red:
        print(f"RED: {', '.join(red)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
