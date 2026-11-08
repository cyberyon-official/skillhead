#!/usr/bin/env python3
"""PreToolUse hook: only issue-publisher creates issues on the guarded repos.

  guard_issue_create.py [<owner/repo>…]
The repos are the arguments plus the plugin option `guarded_repos`
(CLAUDE_PLUGIN_OPTION_GUARDED_REPOS, space-separated). With none, everything
passes. Matchers: Bash, and any MCP tool whose name ends in create_issue.

An issue creation is any of, wherever the command nests it (see
loop-issues/hooks/_shell.py):
  gh issue create | glab issue create|new
  gh api | glab api on an issues endpoint with a write method
    (-X/--method POST, or a field/input flag, which implies POST)
  curl | wget | http | xh writing to a GitHub or GitLab issues endpoint
  an MCP create_issue call (project_id, owner+repo, repository, repo)
Its target: -R/--repo, GH_REPO, the endpoint path, else the cwd's origin.
What stays out of reach: SECURITY.md § Known limits.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "loop-issues" / "hooks"))
import _shell  # noqa: E402  (the plugin's one shell parser)

WRITE_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input"}
ISSUES_PATH = re.compile(r"(?:^|/)(?:repos/([^/\s?]+/[^/\s?]+)|projects/([^/\s?]+(?:/[^/\s?]+)*?))/issues/?(?:[?\s]|$)")
URL_ISSUES = re.compile(r"https?://[^/\s]+/(?:api/v3/|api/v4/)?(repos/[^?\s]+|projects/[^?\s]+)")


def read_input() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8", "replace").strip()
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def norm(repo: str) -> str:
    """`g%2Fp`, `g/p.git`, `git@host:g/p.git`, `https://host/g/p` → `g/p`."""
    repo = repo.strip().replace("%2F", "/").replace("%2f", "/")
    repo = re.sub(r"^(?:[a-z+]+://)?(?:[^@/]+@)?[^/:]+[:/](?=[^/]+/)", "", repo) if re.search(r"[:@]|://", repo) else repo
    return re.sub(r"\.git$", "", repo.strip("/")).lower()


def origin(cwd: str) -> str:
    try:
        out = subprocess.run(["git", "-C", cwd or ".", "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def option(args, *names):
    for k, a in enumerate(args):
        for n in names:
            if a == n and k + 1 < len(args):
                return args[k + 1]
            if n.startswith("--") and a.startswith(n + "="):
                return a[len(n) + 1:]
            if not n.startswith("--") and a.startswith(n) and len(a) > len(n):
                return a[len(n):]
    return None


API_WITH_VALUE = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "-H", "--header", "--input",
                  "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p", "--preview", "-R", "--repo"}


def first_positional(args, with_value):
    skip = False
    for a in args:
        if skip:
            skip = False
        elif a in with_value:
            skip = True
        elif not a.startswith("-"):
            return a
    return ""


def endpoint_repo(path: str):
    m = ISSUES_PATH.search(path.split("?")[0] + " ")
    if not m:
        return None
    return m.group(1) or m.group(2)


def forge_target(cmd, scope_env):
    """(creates an issue?, explicit target or None) for one command."""
    args = cmd.argv[1:]
    env = {**scope_env, **cmd.env}
    if cmd.name in ("gh", "glab"):
        repo = option(args, "-R", "--repo") or (env.get("GH_REPO") if cmd.name == "gh" else None)
        words = [a for a in args if not a.startswith("-")]
        if "issue" in words:
            k = words.index("issue")
            if k + 1 < len(words) and words[k + 1] in ("create", "new"):
                return True, repo
        if "api" in words:
            path = first_positional(args[args.index("api") + 1:], API_WITH_VALUE)
            method = (option(args, "-X", "--method") or "").upper()
            writes = method in ("POST", "PUT") or (not method and any(
                a in WRITE_FLAGS or a.split("=")[0] in WRITE_FLAGS or re.fullmatch(r"-[fF].+", a) for a in args))
            target = endpoint_repo(path)
            if writes and (target is not None or re.search(r"/issues/?$", path.split("?")[0])):
                return True, target if target and "{" not in target else repo
        return False, None
    if cmd.name in ("curl", "wget", "http", "https", "xh"):
        text = " ".join(args)
        for m in URL_ISSUES.finditer(text):
            target = endpoint_repo(m.group(1))
            if target is None:
                continue
            method = (option(args, "-X", "--request", "--method") or "").upper()
            data = any(a.startswith(("-d", "--data", "--json", "-F", "--form", "--post-data", "--post-file"))
                       for a in args)
            if method in ("POST", "PUT") or (not method and data) or cmd.name in ("http", "https", "xh") and any(
                    "=" in a or ":=" in a for a in args if not a.startswith("-")):
                return True, target
        return False, None
    return False, None


def mcp_target(tool: dict):
    for key in ("project_id", "repository", "full_name"):
        if tool.get(key):
            return str(tool[key])
    owner, repo = tool.get("owner"), tool.get("repo")
    if owner and repo:
        return f"{owner}/{repo}"
    if repo and "/" in str(repo):
        return str(repo)
    return None


def targets(data: dict):
    """Every repo the tool call would create an issue on ('' = the cwd's origin)."""
    tool = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    name = str(data.get("tool_name") or "")
    if name.startswith("mcp__") and name.endswith("create_issue") or (not tool.get("command") and mcp_target(tool)):
        target = mcp_target(tool)
        return [target] if target else [""]
    found = []
    for cmd in _shell.commands(str(tool.get("command") or "")):
        creates, target = forge_target(cmd, {})
        if creates:
            found.append(target or "")
    return found


def main(repos) -> int:
    repos = list(repos) + os.environ.get("CLAUDE_PLUGIN_OPTION_GUARDED_REPOS", "").split()
    if not repos:
        return 0
    data = read_input()
    if str(data.get("agent_type") or "").rsplit(":", 1)[-1] == "issue-publisher":
        return 0
    found = targets(data)
    if not found:
        return 0
    guarded = {norm(r) for r in repos}
    for target in found:
        resolved = norm(target) if target else norm(origin(str(data.get("cwd") or ".")))
        if resolved in guarded:
            repo = next(r for r in repos if norm(r) == resolved)
            print(f"Refused: issues on {repo} are created by the /skillhead:issue publisher only. "
                  "Use /skillhead:issue.", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
