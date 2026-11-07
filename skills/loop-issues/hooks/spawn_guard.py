#!/usr/bin/env python3
"""PreToolUse hook (Agent): a phase prompt never names a gate.

The brief owns each phase's gate scope; the prompt hands facts. The gate
commands come from the project profile (`gate_patterns`, see _lib.py).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402


def main(argv):
    data = L.hook_input()
    tool = L.tool_input(data)
    profile = L.load_profile(data.get("cwd"))
    if tool.get("subagent_type") not in profile["guarded_agents"]:
        return 0
    gate = L.first_match(profile["gate_patterns"], str(tool.get("prompt") or ""))
    if gate:
        raise L.Refuse(
            f"Refused: the prompt names a gate (`{gate}`). The brief owns each phase's "
            "gate scope: hand facts and the brief's path only. A merge-queue red sends "
            "the lot back to ship; a lesson that changes a gate goes to /reflect on the brief.")
    return 0


if __name__ == "__main__":
    L.run(main)
