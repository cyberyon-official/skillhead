#!/usr/bin/env python3
"""Mechanical checks of the loop; exit 2 = refused, reason on stderr.

Exit 1 = forge or usage error, never a refusal.
  check.py issue <gh|glab> <project> <n> <template section>…
    LOOP_INTEGRATED="<n>…": blockers merged into the run's integration
    branch, still open on the forge until the closing MR, count as done.
  check.py contract <contract.md>
    Front lot (a `Files` path matches the profile's `frontend`, or
    LOOP_FRONTEND) → each Need owes an e2e/ test. Run in the repo;
    LOOP_BASE (default HEAD): the ref E2e impact paths must exist on.
  check.py overlap <new contract.md> <in-flight contract.md>…
    Paths matching the profile's `generated` (or LOOP_GENERATED) never hold.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

USAGE = "usage: check.py issue|contract|overlap …"
NEED_ID = re.compile(r"(?<!\w)N[0-9]+(?!\w)")


# ---------------------------------------------------------------- issue

def issue_json(forge: str, project: str, n: str) -> dict:
    """{body, open} of issue n of project on forge; Fail on any forge error."""
    if forge == "gh":
        argv = ["gh", "issue", "view", n, "-R", project, "--json", "body,state"]
    elif forge == "glab":
        argv = ["glab", "api", f"projects/{project}/issues/{n}"]
    else:
        raise L.Fail(f"unknown forge: {forge}")
    try:
        out = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
    except OSError as e:
        raise L.Fail(f"{forge}: {e}")
    if out.returncode != 0:
        raise L.Fail(out.stderr.strip())
    try:
        data = json.loads(out.stdout)
    except ValueError:
        raise L.Fail(f"{forge}: unreadable answer for #{n}")
    if forge == "gh":
        return {"body": data.get("body") or "", "open": data.get("state") == "OPEN"}
    return {"body": data.get("description") or "", "open": data.get("state") == "opened"}


def check_issue(forge, project, n, sections, fetch=issue_json):
    body = fetch(forge, project, n)["body"]
    for name in sections:
        if not any(line.startswith("**" + name) for line in body.splitlines()):
            raise L.Refuse("outside template")
    integrated = os.environ.get("LOOP_INTEGRATED", "").replace("#", "").split()
    for m in re.finditer(r"(?i)(blocked by|bloquée? par) #([0-9]+)", body):
        blocker = m.group(2)
        if blocker in integrated:
            continue
        if fetch(forge, project, blocker)["open"]:
            raise L.Refuse(f"blocked by #{blocker}")


# ---------------------------------------------------------------- contract

def files(text: str) -> list:
    for line in L.section(text, "Shapes"):
        if line.startswith("- Files"):
            return L.backticked(line)
    return []


def frontend_re(cwd=None) -> str:
    return os.environ.get("LOOP_FRONTEND") or L.load_profile(cwd).get("frontend") or ""


def generated_re(cwd=None) -> str:
    return os.environ.get("LOOP_GENERATED") or L.load_profile(cwd).get("generated") or ""


NO_READER = re.compile(r"(read by[^:]{0,2}:)[ \t]*([Nn]one|[Nn]obody)[ \t.]*([ \t]—.*)?$")
HAS_READER = re.compile(r"read by[^:]{0,2}:[ \t]*([^\W_]|[`#])")


def check_contract(path):
    text = L.read_text(path)
    needs = [l for l in L.section(text, "Need") if l.startswith("- ")]
    unnamed = next((l for l in needs if not re.match(r"- N[0-9]+ ", l)), None)
    if unnamed:
        raise L.Refuse(f"Need without an N<k> id: {unnamed}")
    test_lines = [l for l in L.section(text, "Tests") if l.startswith("- ")]
    tested = {b for l in test_lines for b in NEED_ID.findall(l)}
    front = frontend_re()
    e2e = None
    if front and any(re.search(front, f) for f in files(text)):
        e2e = {b for l in test_lines if "e2e/" in l for b in NEED_ID.findall(l)}
    no_e2e = []
    for line in needs:
        bid = re.match(r"- (N[0-9]+)", line).group(1)
        if bid not in tested:
            raise L.Refuse(f"Need {bid} has no test")
        if e2e is not None and bid not in e2e:
            no_e2e.append(bid)
    if no_e2e:
        raise L.Refuse("Needs with no e2e/ test: " + " ".join(no_e2e))
    if not files(text):
        raise L.Refuse("Shapes has no '- Files:' line")
    for line in L.section(text, "Shapes"):
        if line.startswith("- changed") and not HAS_READER.search(NO_READER.sub(r"\1", line)):
            name = re.sub(r" — .*", "", re.sub(r"^- changed ", "", line))
            raise L.Refuse(f"no readers for: {name}")
    impact = [l.replace("`", "") for l in L.section(text, "E2e impact") if l.startswith("- ")]
    if not impact:
        raise L.Refuse("E2e impact is missing or empty")
    if any(re.match(r"- [Nn]one — .", l) for l in impact):
        return
    base = os.environ.get("LOOP_BASE") or "HEAD"
    changed_tests = "\n".join(L.section(text, "Changed tests"))
    for line in impact:
        m = re.match(r"- (\S+) — (changed|intact) — .", line)
        if not m:
            raise L.Refuse(f"E2e impact line not '<path> — changed|intact — <reason>': {line}")
        spec, state = m.group(1), m.group(2)
        if L.git("cat-file", "-e", f"{base}:{spec}").returncode != 0:
            raise L.Refuse(f"E2e impact: {spec} not on {base}")
        if state == "changed" and spec not in changed_tests:
            raise L.Refuse(f"E2e impact: {spec} changed but not in Changed tests")


# ---------------------------------------------------------------- overlap

def check_overlap(new, others):
    gen = generated_re()

    def authored(path):
        return {f for f in files(L.read_text(path)) if not (gen and re.search(gen, f))}

    mine = authored(new)
    for other in others:
        shared = sorted(mine & authored(other))
        if shared:
            raise L.Refuse(f"{other}: {' '.join(shared)}")


def main(argv):
    mode = argv[0] if argv else ""
    if mode == "issue" and len(argv) >= 4:
        check_issue(argv[1], argv[2], argv[3], argv[4:])
    elif mode == "contract" and len(argv) == 2:
        check_contract(argv[1])
    elif mode == "overlap" and len(argv) >= 2:
        check_overlap(argv[1], argv[2:])
    else:
        raise L.Fail(USAGE)


if __name__ == "__main__":
    L.run(main)
