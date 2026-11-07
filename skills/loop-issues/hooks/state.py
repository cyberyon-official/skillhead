#!/usr/bin/env python3
"""Reads and marks the loop's state.md; exit 2 = refused, reason on stderr.

Exit 1 = usage or unreadable state, never a refusal.
  state.py tick <state.md>            budget marks, then the loop mode
  state.py model <state.md> <serving model id>
  state.py fresh                      skill files changed since the last read
  state.py count <state.md>           progress counter
  state.py merged <findings.md> <n> <report-dir>
                                      registers the lot's unpaid findings;
                                      prints "audit due" from 10 merges
                                      since the last "audited" line
"""
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

USAGE = "usage: state.py tick|model|fresh|count|merged …"
SLOT = re.compile(r"^slot [0-9]+: .* (loop-[a-z-]+) since (\S+) — (.+)$")
TURTLE = "\U0001F422"


def budget(agent: str) -> int:
    """Budget column (minutes) of the § Agents table of SKILL.md; 0 when none."""
    for line in L.lines(L.SKILL_DIR / "SKILL.md"):
        fields = re.split(r" *\| *", line)
        if len(fields) > 5 and fields[2] == f"`{agent}`":
            m = re.match(r"\s*([0-9]+)", fields[5])
            return int(m.group(1)) if m else 0
    return 0


def tick(state):
    now = L.now()
    out, marks = [], []
    for line in L.lines(state):
        m = SLOT.match(line)
        if m and TURTLE not in line:
            agent, since, report = m.groups()
            limit = budget(agent)
            spent = int((now - L.parse_iso(since)).total_seconds() // 60)
            if limit > 0 and spent > limit:
                line = f"{line} {TURTLE} {spent}/{limit} min"
                marks.append((report, line))
        out.append(line)
    L.write_text(state, "".join(l + "\n" for l in out))
    # After the rewrite, so a failed tick never logs twice.
    for report, line in marks:
        L.append_line(Path(report) / "slowness.md", line)
    mode = next((l[len("mode: "):] for l in out if l.startswith("mode: ")), "")
    if mode.startswith("pause-until "):
        until = mode[len("pause-until "):]
        if L.parse_iso(until) > now:
            raise L.Refuse(f"paused until {until}")
    elif mode == "drain":
        if any(re.match(r"(slot [0-9]+: |held: )#", l) for l in out):
            raise L.Refuse("draining")
        raise L.Refuse("drained")


def model(state, serving):
    pinned = ""
    agent = L.claude_home() / "agents" / "loop-orchestrator.md"
    if agent.is_file():
        for line in L.lines(agent):
            fields = line.split()
            if len(fields) >= 2 and fields[0] == "model:":
                pinned = fields[1]
                break
    if not pinned:
        raise L.Fail("model: no pin in loop-orchestrator.md")
    if serving == pinned:
        return
    L.append_line(state, f"stopped: model — serving {serving}, pinned {pinned}")
    raise L.Refuse(f"model — serving {serving}, pinned {pinned}")


def skill_files():
    for root, dirs, names in os.walk(L.SKILL_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in names:
            if not name.endswith(".pyc"):
                yield Path(root) / name


def fresh():
    mark = L.run_dir() / f"{L.session_id()}.read"
    if not mark.exists():  # the session loaded the skill just before its first call
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.touch()
        return
    since = mark.stat().st_mtime
    changed = sorted(str(p) for p in skill_files() if p.stat().st_mtime > since)
    if changed:
        mark.touch()
        raise L.Refuse("\n".join(changed))


def count(state):
    text = L.read_text(state)
    m = re.search(r"^planned: ([0-9]+) \(\+([0-9]+)\)$", text, re.M)
    if not m:
        raise L.Fail(f"count: no 'planned: N (+k)' line in {state}")
    finished = sum(1 for l in text.splitlines() if l.startswith("done: "))
    print(f"Counter: {finished} / {m.group(1)} lots (+{m.group(2)} added)")


def registered(reg_lines, key):
    """A closed entry: its key, then the audit's closing mark."""
    for line in reg_lines:
        if line.startswith("- [x] "):
            line = re.sub(r" — (absent @\S+|already #[0-9]+|#[0-9]+)$", "", line)
        line = re.sub(r"^- \[[ x]\] ", "", line)
        if line == key:
            return True
    return False


def merged(reg, n, report_dir):
    reg = Path(reg)
    reg.touch()
    for ship in sorted(Path(report_dir).glob("ship-*.md")):
        for finding in L.section(L.read_text(ship), "Unpaid findings"):
            if not finding.startswith("- "):
                continue
            finding = finding[2:]
            if not registered(L.lines(reg), f"#{n} {finding}"):
                L.append_line(reg, f"- [ ] #{n} {finding}")
    L.append_line(reg, f"merged #{n}")
    since = 0  # merges since the last audit; an `audited` line resets the count
    for line in L.lines(reg):
        if line.startswith("audited"):
            since = 0
        elif line.startswith("merged "):
            since += 1
    if since >= 10:
        print("audit due")


def main(argv):
    mode, args = (argv[0] if argv else ""), argv[1:]
    if mode == "tick" and len(args) == 1:
        tick(args[0])
    elif mode == "model" and len(args) == 2:
        model(*args)
    elif mode == "fresh" and not args:
        fresh()
    elif mode == "count" and len(args) == 1:
        count(args[0])
    elif mode == "merged" and len(args) == 3:
        merged(*args)
    else:
        raise L.Fail(USAGE)


if __name__ == "__main__":
    L.run(main)
