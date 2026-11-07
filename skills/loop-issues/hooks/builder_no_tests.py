#!/usr/bin/env python3
"""PreToolUse hook (Bash): no test run per lot by a loop-builder.

A plugin agent cannot carry its own hooks, so this runs on every Bash call
and acts only when the hook input names a loop-builder as `agent_type`.

Matches the raw command, quoted strings included (`bash -c "…"`). The test
commands come from the project profile (`test_patterns`); `test_allowed`
lists the replays the queue may hand back (a named group `keep` survives).
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402


def main(argv):
    data = L.hook_input()
    if L.bare_agent(data.get("agent_type")) != "loop-builder":
        return 0
    command = str(L.tool_input(data).get("command") or "")
    profile = L.load_profile(data.get("cwd"))
    for allowed in profile["test_allowed"]:
        command = re.sub(allowed, lambda m: m.groupdict().get("keep") or "", command)
    if not L.first_match(profile["test_patterns"], command):
        return 0
    hint = profile.get("test_allowed_hint") or ""
    raise L.Refuse(
        "Refused: no test per lot: the merge queue and the closing run them"
        + (f"; only the guard the queue returned may be replayed: {hint}" if hint else "")
        + "; a test the contract requires to run once goes to a loop-mechanic task.")


if __name__ == "__main__":
    L.run(main)
