#!/usr/bin/env python3
"""PreToolUse hook: only issue-publisher creates issues on the listed repos.

  guard_issue_create.py [<owner/repo>…]
The repos are the arguments plus the plugin option `guarded_repos`
(CLAUDE_PLUGIN_OPTION_GUARDED_REPOS, space-separated). Matchers: Bash, and
a forge MCP's create_issue (its project_id). With no repo, everything passes.
"""
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

CALL = r"(^|[;&|(])\s*([A-Za-z0-9_]+=\S*\s+)*(glab|gh)\s+"
WRITE_FLAG = re.compile(r"\s(-f|-F|--field|--raw-field|--input|-XPOST|-X\s+POST|--method\s+POST)")


def read_input() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8", "replace").strip()
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def creates_issue(command: str) -> bool:
    if re.search(CALL + r"issue\s+(create|new)", command, re.M):
        return True
    for m in re.finditer(CALL + r"api\s[^;&|\n]*", command, re.M):
        call = m.group(0)
        if (re.search(r"""/issues([\s?"']|$)""", call) and WRITE_FLAG.search(call)
                and not re.search(r"(-X|--method)\s*GET", call)):
            return True
    return False


def origin(cwd: str) -> str:
    try:
        out = subprocess.run(["git", "-C", cwd or ".", "remote", "get-url", "origin"],
                             capture_output=True, text=True)
    except OSError:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def main(repos) -> int:
    repos = list(repos) + os.environ.get("CLAUDE_PLUGIN_OPTION_GUARDED_REPOS", "").split()
    if not repos:
        return 0
    data = read_input()
    if str(data.get("agent_type") or "").rsplit(":", 1)[-1] == "issue-publisher":
        return 0
    tool = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    command = str(tool.get("command") or "")
    project = str(tool.get("project_id") or "")
    if not (creates_issue(command) or project):
        return 0
    target = "\n".join([command, project, "" if project else origin(str(data.get("cwd") or "."))])
    for repo in repos:
        names = "|".join(map(re.escape, {repo, repo.replace("/", "%2F")}))
        if re.search(r"(^|[\s:/=])(" + names + r")(\.git)?([\s/]|$)", target, re.M):
            print(f"Refused: issues on {repo} are created by the /issue publisher only. Use /issue.",
                  file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
