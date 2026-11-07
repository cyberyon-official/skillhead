#!/usr/bin/env python3
"""start/stop mark the loop; bare (PreToolUse AskUserQuestion): refuse while marked."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

MESSAGE = ("Refused: a loop-issues loop runs in this session, nobody answers. "
           "Report BLOCKED with the question as the reason. "
           "Loop stopped: loop_running.py stop.")


def main(argv):
    mode = argv[0] if argv else ""
    if mode == "start":
        L.run_dir().mkdir(parents=True, exist_ok=True)
        (L.run_dir() / L.session_id()).touch()
    elif mode == "stop":
        (L.run_dir() / L.session_id()).unlink(missing_ok=True)
    else:
        if L.loop_running(L.hook_input().get("session_id")):
            raise L.Refuse(MESSAGE)


if __name__ == "__main__":
    L.run(main)
