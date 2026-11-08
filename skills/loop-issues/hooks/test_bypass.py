#!/usr/bin/env python3
"""Bypass corpora for the guard hooks: python3 skills/loop-issues/hooks/test_bypass.py

Each corpus pairs commands that must be refused (a way around the guard)
with look-alikes that must pass (no false positive). A new bypass found in
the wild is added here first, red, then fixed. SECURITY.md lists what stays
out of reach on purpose.
"""
import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS))
import _shell  # noqa: E402
from test_hooks import ISSUE_GUARD, HookCase, git  # noqa: E402

LOOP = {"agent_type": "skillhead:loop-builder"}


def pwsh(code):
    return base64.b64encode(code.encode("utf-16-le")).decode()


class Parser(unittest.TestCase):
    def argvs(self, text):
        return [c.argv for c in _shell.commands(text)]

    def test_nesting_reaches_the_inner_command(self):
        cases = {
            "a; b && c || d | e & f": ["a", "b", "c", "d", "e", "f"],
            "(cd x && git status)": ["cd", "git"],
            "x=$(git status) y=`git log`": ["git", "git"],
            "diff <(git log) <(git status)": ["git", "git", "diff"],
            "bash -lc 'git status'": ["bash", "git"],
            "eval 'git status'": ["eval", "git"],
            "bash <<'EOF'\ngit status\nEOF": ["bash", "git"],
            "sh <<< 'git status'": ["sh", "git"],
            "echo 'git status' | sh": ["echo", "sh", "git"],
            "cat <<EOF | bash\ngit status\nEOF": ["cat", "bash", "git"],
            "sudo -u x env A=1 nice -n 5 timeout 3 git status": ["sudo", "env", "nice", "timeout", "git"],
            "find . -exec git status \\;": ["git", "find"],
            "xargs -n1 git status": ["xargs", "git"],
            "if true; then git status; fi": ["true", "git"],
            "for f in a; do git status; done": ["git"],
            "case $x in a) git status;; esac": ["git"],
            "f() { git status; }; f": ["f", "git", "f"],
            f"pwsh -EncodedCommand {pwsh('git status')}": ["pwsh", "git"],
            "cmd /c git status": ["cmd", "git"],
            "python3 -c \"import os; os.system('git status')\"": ["python3", "git"],
        }
        for text, names in cases.items():
            self.assertEqual([_shell.basename(a[0]) for a in self.argvs(text)], names, text)

    def test_quotes_escapes_variables_aliases(self):
        self.assertIn(["git", "commit", "--no-verify"], self.argvs('git commit "--no-verify"'))
        self.assertIn(["git", "commit", "--no-verify"], self.argvs("git commit $'\\x2d\\x2dno-verify'"))
        self.assertIn(["git", "commit"], self.argvs("g\\it com'mit'"))
        self.assertIn(["git", "commit", "-n"], self.argvs("G=git; $G commit -n"))
        self.assertIn(["git", "commit", "-n"], self.argvs("export G=git && ${G} commit -n"))
        self.assertIn(["git", "commit", "-n", "-m", "x"], self.argvs("alias gc='git commit -n'; gc -m x"))
        self.assertIn(["git", "commit", "-n"], self.argvs("git commit \\\n -n"))

    def test_data_is_not_code(self):
        for text in ["git commit -F- <<'EOF'\ngit commit --no-verify\nEOF", "echo 'git commit -n' > notes",
                     "cat <<EOF\ngit commit -n\nEOF", "printf '%s' 'git commit -n'", "command -v git",
                     "grep -r 'git commit -n' docs", "echo \"1<<2\""]:
            self.assertNotIn(["git", "commit", "-n"], self.argvs(text), text)
            self.assertNotIn(["git", "commit", "--no-verify"], self.argvs(text), text)

    def test_never_raises_on_any_input(self):
        # A parser crash would make a guard exit 1, which Claude Code does not block
        # on (SECURITY.md, fail-open): the parser must survive anything.
        import random
        rng = random.Random(20261108)
        alphabet = list("ab gitcommn-'\"\\$`(){};&|<>#\n\t=*?!~%^:/.") + ["<<EOF", "EOF", "$(", "<<<", "bash -c "]
        for _ in range(3000):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
            _shell.commands(text)

    def test_redirects_are_not_arguments(self):
        cmd = _shell.commands("git commit -m x 2>&1 >> log.txt")[0]
        self.assertEqual(cmd.argv, ["git", "commit", "-m", "x"])
        self.assertEqual(cmd.redirects, [("2>&", "1"), (">>", "log.txt")])


class HookBypass(HookCase):
    script = HOOKS / "refuse_hook_bypass.py"

    def run_cmd(self, command, cwd=None):
        return self.run_script(self.script, stdin=json.dumps({**LOOP, "tool_input": {"command": command},
                                                              "cwd": str(cwd or self.tmp)}))

    def test_bypasses_are_refused(self):
        for c in [
            'git commit "--no-verify" -m x', "git commit '-n' -m x", "git commit --no-veri -m x",
            "git commit $'\\x2d\\x2dno-verify' -m x", "g\\it commit -n -m x",
            "/usr/bin/git commit -n -m x", "git.exe commit -n -m x", "C:\\\\Git\\\\bin\\\\git.exe commit -n",
            "env git commit -n -m x", "command git commit --no-verify", "sudo -E git commit -n",
            "nice -n 5 git commit -n", "timeout 30 git commit -n", "xargs git commit -n",
            "find . -maxdepth 0 -exec git commit -n -m x \\;",
            "bash -c 'git commit --no-verify -m x'", "sh -ec 'git commit -n'", 'eval "git commit -n -m x"',
            "bash <<'EOF'\ngit commit --no-verify -m x\nEOF", "echo 'git commit -n -m x' | sh",
            "cat <<EOF | bash\ngit commit -n\nEOF", "sh <<< 'git commit -n'",
            f"pwsh -EncodedCommand {pwsh('git commit -n -m x')}", "cmd /c git commit --no-verify",
            "python3 -c \"import subprocess; subprocess.run(['git', 'commit', '-n'])\"",
            "G=git; $G commit -n -m x", "x=--no-verify; git commit $x -m y", "alias gc='git commit -n'; gc -m x",
            "(cd sub && git commit -n -m x)", "x=$(git commit -n -m y)", "git commit -m x \\\n  -n",
            "git commit -am x --no-verify", "git commit -anm x", "git commit -vn",
            "git -c CORE.HOOKSPATH=/dev/null commit -m x", "git -ccore.hooksPath=/x commit -m y",
            "git --config-env=core.hooksPath=HP commit -m x",
            "GIT_CONFIG_PARAMETERS=\"'core.hooksPath=/dev/null'\" git commit -m x",
            "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/x git commit -m y",
            "git config core.hooksPath /dev/null", "git config --global core.hooksPath /x",
            "git config set core.hooksPath /x", "git config alias.c 'commit --no-verify'",
            "git -c alias.c='commit -n' c -m x", "git config alias.p '!git push --no-verify'",
            "SKIP=lint git commit -m x", "HUSKY=0 git commit -m x", "HUSKY_SKIP_HOOKS=1 git commit -m x",
            "git push --no-verify", "git merge --no-verify topic", "git rebase --no-verify main",
            "git am --no-verify < p.patch",
            "rm -f .git/hooks/pre-commit && git commit -m x", "chmod -x .git/hooks/pre-commit",
            "mv .git/hooks/pre-commit /tmp/", "echo exit 0 > .git/hooks/pre-commit",
            "sed -i 1d .git/hooks/pre-commit", "truncate -s0 .git/hooks/pre-push",
            "Remove-Item '.git\\hooks\\pre-commit'", "pwsh -c \"Remove-Item .git\\hooks\\pre-commit\"",
            "cmd /c \"del .git\\hooks\\pre-commit\"",
        ]:
            self.assertEqual(self.run_cmd(c), "deny", c)

    def test_look_alikes_pass(self):
        for c in [
            'git commit -m "--no-verify is forbidden"', "git commit -m x -- -n", "git log -n 3",
            "git commit -uno -m x", "git commit -m n", "git commit -Sn -m x", "git commit -m -n",
            "git config --unset core.hooksPath", "git config --get core.hooksPath", "git config core.hooksPath",
            "git commit -F msg.txt", "echo 'git commit -n' > notes.txt", "cat .git/hooks/pre-commit",
            "git commit --no-verify --verify -m x", "git push -n origin main", "git merge -n topic",
            "grep -rn 'git commit --no-verify' docs", "ls .git/hooks", "command -v git",
            "SKIP= git commit -m x", "HUSKY=1 git commit -m x", "sed -n 1p .git/hooks/pre-commit",
            "git commit -F- <<'EOF'\nNever git commit --no-verify.\nEOF",
            "git config alias.st status", "git status -n",
        ]:
            self.assertEqual(self.run_cmd(c), "pass", c)

    def test_repo_alias_is_resolved(self):
        repo = self.tmp / "aliased"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        git(repo, "config", "alias.ci", "commit --no-verify")
        git(repo, "config", "alias.st", "status")
        self.assertEqual(self.run_cmd("git ci -m x", cwd=repo), "deny")
        self.assertEqual(self.run_cmd("git st", cwd=repo), "pass")


class IssueGuardBypass(HookCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "guarded"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        git(self.repo, "remote", "add", "origin", "https://github.com/g/p.git")

    def guard(self, data):
        return self.run_script(ISSUE_GUARD, args=["g/p"], stdin=json.dumps(data))

    def cmd(self, command, cwd=None):
        return self.guard({"tool_input": {"command": command}, "cwd": str(cwd or self.tmp)})

    def test_bypasses_are_refused(self):
        for c in ["GH_REPO=g/p gh issue create -t x", "env gh issue create -R g/p -t x",
                  "bash -c 'gh issue create -R g/p -t x'", "/usr/local/bin/gh issue create -R g/p -t x",
                  "gh -R g/p issue create -t x", "gh issue create --repo=g/p -t x", "gh issue create -RG/P -t x",
                  "gh api -X POST repos/g/p/issues -f title=x", "gh api repos/g/p/issues --method=POST -f t=x",
                  "gh api repos/g/p/issues -F title=x", "gh api repos/g/p/issues --input body.json",
                  "glab issue create -R g/p -t x", "glab issue new -R g/p",
                  "glab api projects/g%2Fp/issues -X POST -f title=x",
                  "curl -X POST https://api.github.com/repos/g/p/issues -d '{}'",
                  "curl -sS https://api.github.com/repos/g/p/issues --data @body.json",
                  "curl --request POST https://gitlab.com/api/v4/projects/g%2Fp/issues -F title=x",
                  "x=$(gh issue create -R g/p -t x)", "echo y | xargs gh issue create -R g/p -t"]:
            self.assertEqual(self.cmd(c), "deny", c)
        for c in ["gh issue create -t x", "gh api repos/{owner}/{repo}/issues -f title=x"]:
            self.assertEqual(self.cmd(c, cwd=self.repo), "deny", c)

    def test_mcp_tools_are_refused(self):
        for tool in [{"project_id": "g%2Fp"}, {"owner": "g", "repo": "p"}, {"repo": "g/p"},
                     {"repository": "G/P"}]:
            self.assertEqual(self.guard({"tool_name": "mcp__forge__create_issue", "tool_input": tool}), "deny",
                             tool)
        self.assertEqual(self.guard({"tool_name": "mcp__github__create_issue",
                                     "tool_input": {"owner": "o", "repo": "q"}}), "pass")

    def test_look_alikes_pass(self):
        for c in ["gh issue list -R g/p", "gh issue view 3 -R g/p", "gh api repos/g/p/issues",
                  "gh api repos/g/p/issues/12/comments -f body=x", "gh api -X GET repos/g/p/issues -f state=open",
                  "curl https://api.github.com/repos/g/p/issues", "echo 'gh issue create -R g/p'",
                  "rg -n 'gh issue create' docs", "gh issue create -R o/q -t x", "gh pr create -R g/p"]:
            self.assertEqual(self.cmd(c), "pass", c)
        publisher = {"tool_input": {"command": "gh issue create -R g/p -t x"},
                     "agent_type": "skillhead:issue-publisher"}
        self.assertEqual(self.guard(publisher), "pass")


def spawn(prompt, agent="skillhead:loop-builder", **extra):
    return json.dumps({"tool_input": {"subagent_type": agent, "prompt": prompt, **extra}})


class SpawnBypass(HookCase):
    script = HOOKS / "spawn_guard.py"

    def test_disguised_gates_are_refused(self):
        for p in ["then py\u200btest -q", "run cargo\u00a0check", "run cargo\ncheck -p x", "Run PYTEST first",
                  "run \uff50\uff59\uff54\uff45\uff53\uff54", "go\u2060 test ./...", "npm\t\trun   lint"]:
            self.expect("deny", self.script, spawn(p))
        self.expect("deny", self.script, spawn("facts only", description="then run pytest"))

    def test_plain_prompts_pass(self):
        for p in ["Report dir: /r/issue-1", "touched: src/test_utils.py, docs/testing.md",
                  "the pytest fixture names are listed in the contract"[:0] + "Contract at /r/c.md"]:
            self.expect("pass", self.script, spawn(p))


class BuilderBypass(HookCase):
    script = HOOKS / "builder_no_tests.py"

    def run_cmd(self, command):
        return self.run_script(self.script, stdin=json.dumps({**LOOP, "tool_input": {"command": command}}))

    def test_disguised_test_runs_are_refused(self):
        for c in ["skillhead slot gate x y 'pytest'", "p=pytest; $p -q", "py\\test -q", "'pytest' -q", "alias t='go test'; t ./...",
                  "bash -c 'npm test'", "echo pytest | sh", "env CI=1 pytest", "python3 -m 'pytest'"]:
            self.assertEqual(self.run_cmd(c), "deny", c)

    def test_other_commands_pass(self):
        for c in ["git status", "cat tests/test_x.py", "echo 'run pytest later' > notes", "ls tests",
                  "git commit -m 'fix the pytest fixture'", "rg -n 'go test' docs", "gh pr create -t 'npm test fix'"]:
            self.assertEqual(self.run_cmd(c), "pass", c)


if __name__ == "__main__":
    unittest.main(verbosity=1)
