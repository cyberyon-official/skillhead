#!/usr/bin/env python3
"""merge_gate.py <report-dir> <base> <head> [frontend dir…], from the repo.

Exit 2: a front lot whose last QA verdict is not a clean GO.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

WORDS = r"(GO-PROVISIONAL|NO-GO|GO|BLOCKED|ABORTED)"


def verdict_word(text: str) -> str:
    """The first bold word under `## Verdict`, else the first bold verdict, else the title's."""
    inside = False
    for line in text.splitlines():
        if line.startswith("## Verdict"):
            inside = True
            continue
        if inside and "**" in line:
            return line.split("**", 2)[1] if line.count("**") >= 2 else line.split("**", 1)[1]
    m = re.search(r"\*\*" + WORDS + r"\b", text)
    if m:
        return m.group(1)
    first = text.splitlines()[0] if text else ""
    m = re.search(WORDS + r"$", first)
    return m.group(1) if m else ""


def main(argv):
    if len(argv) < 3:
        raise L.Fail("usage: merge_gate.py <report-dir> <base> <head> [frontend dir…]")
    report, base, head, front_dirs = argv[0], argv[1], argv[2], argv[3:]
    if not front_dirs:
        return 0
    diff = L.git("diff", "--name-only", f"{base}...{head}", "--", *front_dirs)
    if diff.returncode != 0:
        raise L.Fail(diff.stderr.strip())
    if not diff.stdout.strip():
        return 0
    last, verdict = 0, None
    for f in (Path(report) / "qa").glob("verdict-*.md"):
        rnd = f.name[len("verdict-"):-len(".md")]
        if rnd.isdigit() and int(rnd) > last:
            last, verdict = int(rnd), f
    if verdict is None:
        raise L.Refuse(f"BLOCKED — missing QA GO: {report}/qa/verdict-1.md")
    word = verdict_word(L.read_text(verdict)).rstrip(".")
    if word in ("GO", "GO-PROVISIONAL"):
        return 0
    raise L.Refuse(f"BLOCKED — missing QA GO: {report}/qa/{verdict.name} ({word or 'no verdict'})")


if __name__ == "__main__":
    L.run(main)
