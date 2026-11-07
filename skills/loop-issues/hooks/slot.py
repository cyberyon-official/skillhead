#!/usr/bin/env python3
"""Per-slot lifecycle of the loop; exit 2 = refused, reason on stderr.

Exit 1 = usage error, never a refusal. Every value comes from the launch pack.
  slot.py disk <threshold GB> <worktrees dir> <sweep command|-> [<n in flight>…]
  slot.py env        PreToolUse Bash hook: sources <worktrees dir>/slot-<s>.env
  slot.py gate <schema signal regex> <recreate command> <gate command>
  slot.py qa-up <qa-stack.md> <log> <launch command> <port>…
  slot.py qa-probe <dependency>=<command>…
  slot.py qa-down <qa-stack.md>

Launch-pack commands are POSIX shell; they run under bash (Git Bash on
Windows, see _lib.shell_argv).
"""
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib as L  # noqa: E402

USAGE = "usage: slot.py disk|env|gate|qa-up|qa-probe|qa-down …"
WINDOWS = os.name == "nt"
SLOT_PATH = re.compile(
    r"""[^\s"'=;]*-worktrees[\\/]((slot|issue)-[0-9]+|loop-[0-9]{4}-[0-9]{2}-[0-9]{2}[a-z0-9]*(-[a-z0-9]+)*)""")


# ---------------------------------------------------------------- disk

def free_gb(path) -> int:
    p = Path(path)
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return shutil.disk_usage(p).free // 2 ** 30
    except OSError:
        return 0


def disk(threshold, worktrees, sweep, live):
    threshold = int(threshold)
    worktrees = Path(worktrees)

    def roomy():
        return free_gb(worktrees) >= threshold

    if roomy():
        return
    if sweep != "-":
        L.sh(sweep)
    if roomy():
        return
    kept = []  # worktrees git refused to remove, with its reason
    for wt in sorted(worktrees.glob("issue-*")):
        if not wt.is_dir():
            continue
        n = wt.name[len("issue-"):].split("-t", 1)[0]
        if n in live:
            continue
        gitdir = L.git("-C", str(wt), "rev-parse", "--absolute-git-dir").stdout.strip()
        index = Path(gitdir) / "index"
        if gitdir and index.exists() and time.time() - index.stat().st_mtime < 1200 * 60:
            continue
        # Without --force, git refuses a worktree holding uncommitted work.
        # A split issue's env outlives its task worktrees.
        # git's own spelling of the path: on Windows a temp dir may come as an
        # 8.3 short name (RUNNER~1) that `worktree remove` does not match.
        top = L.git("-C", str(wt), "rev-parse", "--show-toplevel").stdout.strip() or str(wt)
        # Run from the main worktree, never from the one being removed:
        # Windows refuses to delete a process's current directory.
        listing = L.git("-C", str(wt), "worktree", "list", "--porcelain").stdout.splitlines()
        main = next((l[len("worktree "):] for l in listing if l.startswith("worktree ")), str(wt))
        removed = L.git("-C", main, "worktree", "remove", top)
        if removed.returncode != 0:
            reason = (removed.stderr.strip().splitlines() or ["?"])[-1]
            kept.append(f"{wt.name} ({reason})")
        elif wt.name == f"issue-{n}":
            (worktrees / f"issue-{n}.env").unlink(missing_ok=True)
    if not roomy():
        detail = f"; kept: {', '.join(kept)}" if kept else ""
        raise L.Refuse(f"disk: {free_gb(worktrees)} GB free < {threshold} GB{detail}")


# ---------------------------------------------------------------- env hook

def env_hook():
    data = L.hook_input()
    tool = L.tool_input(data)
    command = str(tool.get("command") or "")
    cwd = str(data.get("cwd") or "")
    slot = None
    for line in command.splitlines() + [cwd]:
        m = SLOT_PATH.search(line)
        if m:
            slot = m.group(0)
            break
    if not slot:
        return
    if slot.startswith("~/"):
        slot = str(Path.home() / slot[2:])
    elif slot.startswith("$HOME/"):
        slot = str(Path.home() / slot[6:])
    elif not os.path.isabs(slot) and not slot.startswith("/"):
        slot = str(Path(cwd) / slot)
    env = Path(slot + ".env")
    if not env.is_file():
        return
    # No permissionDecision: the rewritten command meets the user's policy.
    prefix = f"set -a; . {shlex.quote(env.as_posix())}; set +a; "
    updated = dict(tool, command=prefix + command)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "updatedInput": updated}}, ensure_ascii=False))


# ---------------------------------------------------------------- gate

def gate(signal_re, recreate, command):
    for attempt in (1, 2):
        run = L.sh(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = run.stdout.decode("utf-8", "replace")
        tail = log.splitlines()[-40:]
        if tail:
            print("\n".join(tail))
        sys.stdout.flush()
        code = run.returncode
        if not (code != 0 and re.search(signal_re, log)):
            return 1 if code == 2 else code  # a gate's own 2 is a red, not a refusal
        if attempt == 2:
            raise L.Refuse("BLOCKED: schema mismatch after recreate")
        if L.sh(recreate, stdout=sys.stderr).returncode != 0:
            raise L.Refuse(f"BLOCKED: recreate failed: {recreate}")
    return 0


# ---------------------------------------------------------------- QA stack

def listening(port) -> bool:
    """A listener on the port, IPv4 or IPv6 loopback."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((host, int(port))) == 0:
                    return True
        except OSError:
            continue
    return False


def field(stack, key):
    return [l.split()[1] for l in L.lines(stack) if len(l.split()) >= 2 and l.split()[0] == key + ":"]


def qa_up(stack, log, launch, ports):
    for port in ports:
        if listening(port):
            raise L.Refuse(f"qa-up: port {port} already held")
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS \
        else {"start_new_session": True}  # the stack gets its own process group
    with open(log, "wb") as out:
        proc = subprocess.Popen(L.shell_argv(launch), stdout=out, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, **kwargs)
    L.write_text(stack, f"pgid: {proc.pid}\n" + "".join(f"port: {p}\n" for p in ports)
                 + f"log: {log}\n")


def qa_probe(probes):
    for probe in probes:
        name, _, command = probe.partition("=")
        if L.sh(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
            raise L.Refuse(f"qa-probe: {name} failed")


def group_alive(pgid) -> bool:
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pgid}"], capture_output=True, text=True)
        return str(pgid) in out.stdout
    try:
        os.killpg(pgid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def kill_group(pgid, force=False):
    if WINDOWS:
        subprocess.run(["taskkill", "/T", "/PID", str(pgid)] + (["/F"] if force else []),
                       capture_output=True)
        return
    try:
        os.killpg(pgid, signal.SIGKILL if force else signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def qa_down(stack):
    if not Path(stack).is_file():
        return
    pgids = field(stack, "pgid")
    if pgids and pgids[0].isdigit():
        pgid = int(pgids[0])
        if group_alive(pgid):
            kill_group(pgid)
            for _ in range(10):
                if not group_alive(pgid):
                    break
                time.sleep(0.5)
            kill_group(pgid, force=True)
    # The kernel frees a dead process's listener asynchronously: give it a
    # few seconds before calling the port held (a slow runner needs them).
    for port in field(stack, "port"):
        for _ in range(20):
            if not listening(port):
                break
            time.sleep(0.25)
        else:
            raise L.Refuse(f"qa-down: port {port} still held")


def main(argv):
    mode, args = (argv[0] if argv else ""), argv[1:]
    if mode == "disk" and len(args) >= 3:
        disk(args[0], args[1], args[2], args[3:])
    elif mode == "env":
        env_hook()
    elif mode == "gate" and len(args) == 3:
        return gate(*args)
    elif mode == "qa-up" and len(args) >= 4:
        qa_up(args[0], args[1], args[2], args[3:])
    elif mode == "qa-probe":
        qa_probe(args)
    elif mode == "qa-down" and len(args) == 1:
        qa_down(args[0])
    else:
        raise L.Fail(USAGE)


if __name__ == "__main__":
    L.run(main)
