#!/usr/bin/env python3
"""Checks the loop's hooks: python3 loop-issues/hooks/test_hooks.py

Stdlib unittest, Linux/macOS/Windows. Needs git on PATH; the QA-stack and
gate cases also need a POSIX shell (bash, Git Bash on Windows).
"""
import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from datetime import timedelta
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS))
import _lib as L  # noqa: E402
import check  # noqa: E402
import slot  # noqa: E402
import state  # noqa: E402

ISSUE_GUARD = HOOKS.parent.parent / "issue" / "hooks" / "guard_issue_create.py"
PROFILE = HOOKS.parent / "profiles" / "rust-pnpm-monorepo.json"
HAS_SHELL = Path(L.shell_argv("true")[0]).name.lower().startswith(("bash", "sh"))


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


def iso(seconds):
    return (L.now() + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


class HookCase(unittest.TestCase):
    """Runs scripts as Claude Code would: subprocess, JSON on stdin, exit code."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = dict(os.environ, HOME=str(self.tmp), USERPROFILE=str(self.tmp),
                        PYTHONDONTWRITEBYTECODE="1")
        for k in ("LOOP_PROFILE", "LOOP_FRONTEND", "LOOP_GENERATED", "LOOP_INTEGRATED", "LOOP_BASE"):
            self.env.pop(k, None)
        self.patch = mock.patch.dict(os.environ, self.env, clear=True)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, script, args=(), stdin="", env=None, cwd=None):
        p = subprocess.run([sys.executable, str(script), *args], input=stdin.encode("utf-8"),
                           capture_output=True, env=dict(self.env, **(env or {})), cwd=cwd)
        self.reason = p.stderr.decode("utf-8").strip()
        self.out = p.stdout.decode("utf-8")
        return {0: "pass", 2: "deny"}.get(p.returncode, "error")

    def expect(self, want, script, stdin="", args=(), **kw):
        got = self.run_script(script, args, stdin, **kw)
        self.assertEqual(got, want, f"{script.name} {list(args)} {stdin!r}: {self.reason}")

    def call(self, fn, *args):
        """In-process: pass | deny | error, the reason in self.reason."""
        self.reason, out = "", io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                fn(*args)
            return "pass"
        except L.Refuse as e:
            self.reason = str(e)
            return "deny"
        except L.Fail as e:
            self.reason = str(e)
            return "error"
        finally:
            self.out = out.getvalue()

    @staticmethod
    def command(c, cwd=None, agent=None, session=None):
        data = {"tool_input": {"command": c}, "cwd": cwd or "."}
        if agent:
            data["agent_type"] = agent
        if session:
            data["session_id"] = session
        return json.dumps(data)


class Bypass(HookCase):
    script = HOOKS / "refuse_hook_bypass.py"

    def test_refused(self):
        for c in ["git commit --no-verify -m x", "git commit -n", "cd x && git -C y commit -nm x",
                  "git commit -an -m x", "git commit -m \"it's\" -n",
                  "git config core.hooksPath /dev/null", "git -c core.hooksPath=/dev/null commit -m x",
                  "git commit \\\n  --no-verify -m x",
                  "cat > f <<EOF\nx\nEOF\njq . <<<y\ngit commit --no-verify -F f",
                  "echo \"1<<2\"\ngit commit --no-verify -m x"]:
            self.expect("deny", self.script, self.command(c, agent="skillhead:loop-builder"))

    def test_plain_git_passes(self):
        for c in ["git commit -m x", 'git commit -am "doc: forbid --no-verify"',
                  "git config --get core.hooksPath", "git log -n 3", "git log --grep=commit -n 3",
                  "git status -uno", "git log -n 5", "git diff --name-only", "git commit -uno -m x",
                  "git commit -amn", "git commit -m \"it's x\" && git log --format='%h' -n 5",
                  "git commit -F- <<'EOF'\nRefuses git commit --no-verify.\nEOF"]:
            self.expect("pass", self.script, self.command(c, agent="skillhead:loop-builder"))

    def test_scoped_to_the_loop(self):
        c = "git commit --no-verify -m x"
        self.expect("pass", self.script, self.command(c))                       # plain session
        self.expect("pass", self.script, self.command(c, agent="general-purpose"))
        self.expect("pass", HOOKS / "loop_running.py", args=["start"], env={"CLAUDE_CODE_SESSION_ID": "s9"})
        self.expect("deny", self.script, self.command(c, session="s9"))          # loop running here
        self.expect("pass", self.script, self.command(c, session="s8"))


class Running(HookCase):
    script = HOOKS / "loop_running.py"

    def test_question_refused_while_running_then_allowed(self):
        self.expect("pass", self.script, args=["start"], env={"CLAUDE_CODE_SESSION_ID": "s1"})
        self.expect("deny", self.script, '{"session_id":"s1"}')
        self.assertIn("BLOCKED", self.reason)
        self.expect("pass", self.script, '{"session_id":"s2"}')
        self.expect("pass", self.script, args=["stop"], env={"CLAUDE_CODE_SESSION_ID": "s1"})
        self.expect("pass", self.script, '{"session_id":"s1"}')

    def test_start_needs_a_session(self):
        self.expect("error", self.script, args=["start"], env={"CLAUDE_CODE_SESSION_ID": ""})


class IssueGuard(HookCase):
    def setUp(self):
        super().setUp()
        self.guarded = self.tmp / "guarded"
        subprocess.run(["git", "init", "-q", str(self.guarded)], check=True)
        git(self.guarded, "remote", "add", "origin", "git@forge:g/p.git")

    def test_refused_on_listed(self):
        for stdin in [self.command("glab api projects/g%2Fp/issues -f title=x"),
                      self.command("gh issue create -R g/p -t x"),
                      self.command("gh issue create -t x", str(self.guarded)),
                      '{"tool_name":"mcp__gitlab__create_issue","tool_input":{"project_id":"g%2Fp"}}']:
            self.expect("deny", ISSUE_GUARD, stdin, args=["g/p"])

    def test_publisher_and_unlisted_pass(self):
        publisher = json.loads(self.command("gh issue create -t x", str(self.guarded)))
        publisher["agent_type"] = "issue-publisher"
        self.expect("pass", ISSUE_GUARD, json.dumps(publisher), args=["g/p"])
        self.expect("pass", ISSUE_GUARD, self.command("gh issue create -R o/q -t x"), args=["g/p"])
        self.expect("pass", ISSUE_GUARD, self.command("glab api projects/g%2Fp/issues/12/notes -f body=x"), args=["g/p"])
        self.expect("pass", ISSUE_GUARD, self.command("gh issue create -R g/p -t x"))
        self.expect("pass", ISSUE_GUARD, self.command("rg -n 'gh issue create' docs", str(self.guarded)), args=["g/p"])

    def test_plugin_option_and_scoped_publisher(self):
        option = {"CLAUDE_PLUGIN_OPTION_GUARDED_REPOS": "o/q g/p"}
        self.expect("deny", ISSUE_GUARD, self.command("gh issue create -R g/p -t x"), env=option)
        self.expect("pass", ISSUE_GUARD, self.command("gh issue create -R g/p -t x",
                                                      agent="skillhead:issue-publisher"), env=option)
        self.expect("pass", ISSUE_GUARD, self.command("gh issue create -R z/z -t x"), env=option)


class MergeGate(HookCase):
    script = HOOKS / "merge_gate.py"

    def setUp(self):
        super().setUp()
        self.repo, self.report = self.tmp / "repo", self.tmp / "report"
        (self.report / "qa").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        for d in ("web", "api"):
            (self.repo / d).mkdir()
            (self.repo / d / "a").touch()
        git(self.repo, "commit", "-qm", "x", "--allow-empty")
        for path in ("api/a", "web/a"):
            git(self.repo, "add", path)
            git(self.repo, "commit", "-qm", "x")

    def verdict(self, n, word, extra=""):
        L.write_text(self.report / "qa" / f"verdict-{n}.md", f"## Verdict\n\n**{word}** — x\n{extra}\n")

    def gate(self, want, base="HEAD~2", head="HEAD"):
        self.expect(want, self.script, args=[str(self.report), base, head, "web"], cwd=self.repo)

    def test_verdicts(self):
        self.gate("pass", head="HEAD~1")                       # back lot: no verdict needed
        self.gate("deny")
        self.assertRegex(self.reason, r"missing QA GO: .*/qa/verdict-1\.md")
        self.verdict(1, "NO-GO")
        self.gate("deny")
        self.assertIn("verdict-1.md (NO-GO)", self.reason)
        self.verdict(2, "GO-PROVISIONAL", "| 3 | UI | / | x | BLOCKED(budget) | - |")
        self.gate("pass")
        self.verdict(3, "GO")
        self.gate("pass")
        self.verdict(4, "GO-PROVISIONAL.")
        self.gate("pass")
        self.verdict(4, "GO-PROVISIONAL", "Tally: 9 BLOCKED(env), 0 BLOCKED(budget).")
        self.gate("pass")
        L.write_text(self.report / "qa" / "verdict-5.md", "# QA run 5 — GO\n")
        self.gate("pass")
        L.write_text(self.report / "qa" / "verdict-6.md", "# QA run 6\n\n**ABORTED.** x\n")
        self.gate("deny")
        self.verdict(9, "GO")
        self.verdict(10, "NO-GO")
        self.gate("deny")
        self.assertIn("verdict-10.md (NO-GO)", self.reason)


SECTIONS = ["Category", "Summary", "Current behavior", "Desired behavior", "Acceptance criteria"]


class CheckIssue(HookCase):
    def setUp(self):
        super().setUp()
        self.forge = {}

    def issue(self, n, opened, *lines):
        body = "\n".join([*lines, "**Category:** bug", "**Summary:** x", "**Current behavior:**", "x",
                          "**Desired behavior:**", "x", "**Acceptance criteria:**", "- [ ] x"])
        self.forge[str(n)] = {"body": body, "open": opened}

    def fetch(self, forge, project, n):
        if n not in self.forge:
            raise L.Fail(f"404 #{n}")
        return self.forge[n]

    def check(self, n, sections=SECTIONS, forge="gh"):
        return self.call(check.check_issue, forge, "g/p", str(n), sections, self.fetch)

    def test_blocked_skipped(self):
        self.issue(1, True, "> **Blocked by #7** — needs the table")
        self.issue(7, True)
        for forge in ("gh", "glab"):
            self.assertEqual(self.check(1, forge=forge), "deny")
            self.assertEqual(self.reason, "blocked by #7")
        self.issue(5, True, "Bloquée par #7")
        self.assertEqual(self.check(5), "deny")
        self.assertEqual(self.reason, "blocked by #7")

    def test_integrated_blocker_passes(self):
        self.issue(1, True, "Blocked by #7")
        self.issue(7, True)
        for integrated, want in (("3 7", "pass"), ("#3 #7", "pass"), ("17", "deny")):
            with mock.patch.dict(os.environ, {"LOOP_INTEGRATED": integrated}):
                self.assertEqual(self.check(1), want, integrated)

    def test_closed_blocker_passes(self):
        self.issue(7, True, "Blocked by #70")
        self.issue(70, False)
        self.assertEqual(self.check(7), "pass")

    def test_forge_error(self):
        self.issue(4, True, "Blocked by #98")
        self.assertEqual(self.check(99), "error")
        self.assertEqual(self.check(4), "error")

    def test_outside_template(self):
        self.forge["2"] = {"body": "**Category:** bug\n**Summary:** x\n**Current behavior:**\nx\n"
                                   "**Desired behavior:**\nx", "open": True}
        self.assertEqual(self.check(2), "deny")
        self.assertEqual(self.reason, "outside template")

    def test_translated_template_passes(self):
        self.forge["3"] = {"body": "**Catégorie :** bug\n**Résumé :** x\n**Comportement actuel :**\nx\n"
                                   "**Comportement attendu :**\nx\n**Critères d'acceptation :**\n- [ ] x",
                           "open": True}
        fr = ["Catégorie", "Résumé", "Comportement actuel", "Comportement attendu", "Critères d'acceptation"]
        self.assertEqual(self.check(3, fr), "pass")


class CheckContract(HookCase):
    def contract(self, *lines):
        path = self.tmp / "c.md"
        L.write_text(path, "\n".join(lines) + "\n")
        return path

    def check(self, path, cwd=None):
        old = os.getcwd()
        os.chdir(cwd or self.tmp)
        try:
            return self.call(check.check_contract, path)
        finally:
            os.chdir(old)

    def test_uncovered_besoin(self):
        c = self.contract("## Need", "- N1 — x", "- N10 — y", "", "## Tests", "- N10 — t",
                          "N1 has no test, prose only.", "", "## Shapes", "- Files: `a/x.md`")
        self.assertEqual(self.check(c), "deny")
        self.assertIn("N1 ", self.reason)

    def test_front_lists_every_besoin_without_e2e(self):
        c = self.contract("## Need", "- N1 — x", "- N2 — y", "- N3 — z", "", "## Tests",
                          "- N1 — e2e/a.spec.ts", "- N2 — t", "- N3 — t", "", "## Shapes",
                          "- Files: `apps/web/x.ts`")
        with mock.patch.dict(os.environ, {"LOOP_FRONTEND": "^apps/web/"}):
            self.assertEqual(self.check(c), "deny")
        self.assertEqual(self.reason, "Needs with no e2e/ test: N2 N3")
        with mock.patch.dict(os.environ, {"LOOP_PROFILE": str(PROFILE)}):  # same, from the profile
            self.assertEqual(self.check(c), "deny")

    def test_missing_readers(self):
        head = ["## Need", "- N1 — x", "", "## Tests", "- N1 — t", "", "## Shapes", "- Files: `foo`"]
        self.assertEqual(self.check(self.contract(*head, "- changed `foo` — x")), "deny")
        self.assertIn("foo", self.reason)
        for readers in ["read by: ", "read by:\t", "read by nobody, cf. a:b", "read by: none",
                        "read by: none.", "read by: nobody — x"]:
            self.assertEqual(self.check(self.contract(*head, f"- changed `foo` — {readers}")), "deny", readers)
            self.assertIn("foo", self.reason)

    def test_complete_passes(self):
        c = self.contract("## Need", "- N1 — x", "", "## Tests", "- N1 — t", "", "## Shapes",
                          "- Files: `foo`", "- changed `foo` — read by: bar",
                          "- changed `baz` — read by : qux", "- changed `quux` — read by: Nobody::new",
                          "", "## E2e impact", "- none — x")
        self.assertEqual(self.check(c), "pass", self.reason)

    def test_impact_e2e(self):
        repo = self.tmp / "guarded"
        (repo / "e2e").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "e2e" / "a.spec.ts").touch()
        git(repo, "add", "e2e")
        git(repo, "commit", "-qm", "t")

        def c(changed, impact):
            return self.contract("## Need", "- N1 — x", "", "## Tests", "- N1 — t", "", "## Shapes",
                                 "- Files: `foo`", "", "## Changed tests", changed, "",
                                 "## E2e impact", impact)

        for impact in ["", "- e2e/b.spec.ts — intact — x", "- e2e/a.spec.ts — changed"]:
            self.assertEqual(self.check(c("- `e2e/a.spec.ts` — x", impact), repo), "deny", impact)
        self.assertEqual(self.check(c("none", "- `e2e/a.spec.ts` — changed — x"), repo), "deny")
        self.assertEqual(self.check(c("- `e2e/a.spec.ts` — x", "- `e2e/a.spec.ts` — changed — x"), repo),
                         "pass", self.reason)


class Overlap(HookCase):
    def formes(self, name, *paths):
        path = self.tmp / name
        L.write_text(path, "## Shapes\n- Files: " + ", ".join(f"`{p}`" for p in paths) + "\n")
        return str(path)

    def test_overlap(self):
        new = self.formes("new.md", "a/x.md", "a/y.md")
        other = self.formes("other.md", "a/x.md", "a/z.md")
        self.assertEqual(self.call(check.check_overlap, new, [other]), "deny")
        self.assertEqual(self.reason, f"{other}: a/x.md")
        other = self.formes("other.md", "b/x.md", "b/z.md")
        self.assertEqual(self.call(check.check_overlap, new, [other]), "pass")
        new = self.formes("new.md", "a/x.md", "a/openapi.json")
        other = self.formes("other.md", "a/z.md", "a/openapi.json")
        with mock.patch.dict(os.environ, {"LOOP_GENERATED": r"openapi\.json$"}):
            self.assertEqual(self.call(check.check_overlap, new, [other]), "pass")

    def test_cli(self):
        new = self.formes("new.md", "a/x.md")
        self.expect("deny", HOOKS / "check.py", args=["overlap", new, new])
        self.expect("error", HOOKS / "check.py", args=["nope"])


class Disk(HookCase):
    def setUp(self):
        super().setUp()
        self.repo, self.wts = self.tmp / "repo", self.tmp / "wts"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        L.write_text(self.repo / "f", "a\n")
        git(self.repo, "add", "f")
        git(self.repo, "commit", "-qm", "a")
        self.wts.mkdir()
        old = time.time() - 30 * 86400
        for n in ("1", "2", "3", "4-t2"):
            git(self.repo, "worktree", "add", "-q", str(self.wts / f"issue-{n}"), "-b", f"agent/issue-{n}")
            os.utime(self.repo / ".git" / "worktrees" / f"issue-{n}" / "index", (old, old))
        L.write_text(self.wts / "issue-3" / "f", "b\n")

    def disk(self, roomy, *args):
        with mock.patch.object(slot, "free_gb", lambda _: 50 if roomy() else 1):
            return self.call(slot.disk, "20", *args)

    def test_below_threshold_held(self):
        self.assertEqual(self.disk(lambda: False, str(self.tmp / "empty-wts"), "-", []), "deny")
        self.assertEqual(self.reason, "disk: 1 GB free < 20 GB")

    @unittest.skipUnless(HAS_SHELL, "needs a POSIX shell")
    def test_sweeps_clones_first(self):
        swept = self.tmp / "swept"
        sweep = f"echo x >> '{(self.tmp / 'sweeps').as_posix()}'; touch '{swept.as_posix()}'"
        self.assertEqual(self.disk(swept.exists, str(self.wts), sweep, ["2"]), "pass")
        self.assertEqual(len(L.lines(self.tmp / "sweeps")), 1)
        self.assertTrue((self.wts / "issue-1").is_dir())

    def test_reclaims_then_passes(self):
        (self.wts / "issue-1.env").touch()
        (self.wts / "issue-4.env").touch()
        self.assertEqual(self.disk(lambda: not (self.wts / "issue-1").is_dir(), str(self.wts), "-", ["2"]),
                         "pass", self.reason)
        self.assertFalse((self.wts / "issue-1").exists() or (self.wts / "issue-1.env").exists())
        self.assertFalse((self.wts / "issue-4-t2").exists())
        self.assertTrue((self.wts / "issue-4.env").exists(), "split issue env lost")
        self.assertEqual(L.git("-C", str(self.repo), "rev-parse", "-q", "--verify", "agent/issue-1").returncode, 0)
        self.assertTrue((self.wts / "issue-2").is_dir())
        self.assertEqual(L.read_text(self.wts / "issue-3" / "f"), "b\n")


@unittest.skipUnless(HAS_SHELL, "needs a POSIX shell")
class EnvHook(HookCase):
    def run_hook(self, command, cwd):
        self.expect("pass", HOOKS / "slot.py", self.command(command, str(cwd)), args=["env"])
        if not self.out.strip():
            return ""
        out = json.loads(self.out)["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", out)
        run = L.sh(out["updatedInput"]["command"], capture_output=True, env=self.env)
        return run.stdout.decode().strip()

    def test_injects_slot_env(self):
        x = self.tmp / "x-worktrees"
        (x / "issue-1-t2" / "sub").mkdir(parents=True)
        (x / "issue-1").mkdir()
        L.write_text(x / "issue-1.env", "FOO=bar\n")
        xp = x.as_posix()
        self.assertEqual(self.run_hook(f'cd {xp}/issue-1 && echo "$FOO"', self.tmp), "bar")
        self.assertEqual(self.run_hook('echo "$FOO"', x / "issue-1-t2" / "sub"), "bar", "split lot cwd")
        self.assertEqual(self.run_hook('cd $HOME/x-worktrees/issue-1 && echo "$FOO"', self.tmp), "bar")
        self.assertEqual(self.run_hook(f"ls {xp}/issue-10/x", self.tmp), "", "issue-10 took issue-1's env")
        (x / "slot-2").mkdir()
        L.write_text(x / "slot-2.env", "FOO=baz\n")
        self.assertEqual(self.run_hook('echo "$FOO"', x / "slot-2"), "baz")
        (x / "loop-2026-10-15").mkdir()
        L.write_text(x / "loop-2026-10-15.env", "FOO=lp\n")
        self.assertEqual(self.run_hook('echo "$FOO"', x / "loop-2026-10-15"), "lp")


@unittest.skipUnless(HAS_SHELL, "needs a POSIX shell")
class Gate(HookCase):
    script = HOOKS / "slot.py"

    def test_recreates_once(self):
        t = self.tmp.as_posix()
        self.expect("pass", self.script, args=["gate", "schema mismatch",
                                               f"echo r >> {t}/recreates; touch {t}/migrated",
                                               f"[ -e {t}/migrated ] || {{ echo schema mismatch; exit 1; }}"])
        self.assertEqual(len(L.lines(self.tmp / "recreates")), 1)
        self.expect("deny", self.script, args=["gate", "schema mismatch", f"echo r >> {t}/recreates2",
                                               "echo schema mismatch; exit 1"])
        self.assertTrue(self.reason.startswith("BLOCKED"))
        self.assertEqual(len(L.lines(self.tmp / "recreates2")), 1)
        p = subprocess.run([sys.executable, str(self.script), "gate", "schema mismatch",
                            f"touch {t}/recreates3", "exit 3"], capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 3)
        self.assertFalse((self.tmp / "recreates3").exists())
        p = subprocess.run([sys.executable, str(self.script), "gate", "schema mismatch", "true", "exit 2"],
                           capture_output=True, env=self.env)
        self.assertEqual(p.returncode, 1, "a gate's own exit 2 read as a refusal")


def free_ports(n):
    """n ports free on 0.0.0.0 and on :: (a listener on [::1] must count)."""
    held, ports = [], []
    for _ in range(200):
        if len(ports) == n:
            break
        v4 = socket.socket()
        v4.bind(("0.0.0.0", 0))
        port = v4.getsockname()[1]
        if socket.has_ipv6:
            try:
                v6 = socket.socket(socket.AF_INET6)
            except OSError:  # no IPv6 on this host: v4 alone decides
                v6 = None
            if v6 is not None:
                try:
                    v6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                    v6.bind(("::", port))
                    held.append(v6)
                except OSError:
                    v6.close()
                    v4.close()
                    continue
        held.append(v4)
        ports.append(port)
    for s in held:
        s.close()
    return ports


def up(port):
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            return True
        except OSError:
            time.sleep(0.5)
    return False


@unittest.skipUnless(HAS_SHELL, "needs a POSIX shell")
class QaStack(HookCase):
    script = HOOKS / "slot.py"

    def serve(self, port):
        return f"'{Path(sys.executable).as_posix()}' -m http.server {port} --bind 127.0.0.1"

    def tearDown(self):
        for stack in self.tmp.glob("qa*.md"):
            self.run_script(self.script, ["qa-down", str(stack)])
        super().tearDown()

    def test_probe_then_down_frees_slot(self):
        (a,) = free_ports(1)
        s, log = self.tmp / "qa1.md", self.tmp / "qa1.log"
        self.expect("pass", self.script, args=["qa-up", str(s), str(log), self.serve(a), str(a)])
        self.assertTrue(up(a), "stack down")
        time.sleep(0.3)
        self.assertIn("GET /", L.read_text(log))
        self.expect("deny", self.script, args=["qa-probe", "idp=true", "cors=false", "port=false"])
        self.assertIn("cors", self.reason)
        self.assertNotIn("port", self.reason)
        self.expect("pass", self.script, args=["qa-down", str(s)])
        self.assertFalse(slot.listening(a))
        self.expect("pass", self.script, args=["qa-down", str(s)])
        self.expect("pass", self.script, args=["qa-down", str(self.tmp / "absent.md")])

    def test_two_slots_no_conflict(self):
        a, b = free_ports(2)
        for n, port in ((1, a), (2, b)):
            self.expect("pass", self.script, args=["qa-up", str(self.tmp / f"qa{n}.md"),
                                                   str(self.tmp / f"qa{n}.log"), self.serve(port), str(port)])
        self.assertTrue(up(a) and up(b))
        self.expect("deny", self.script, args=["qa-up", str(self.tmp / "qa3.md"), str(self.tmp / "qa3.log"),
                                               self.serve(a), str(a)])
        self.assertIn(f"port {a}", self.reason)
        self.assertTrue(up(a))
        for n in (1, 2):
            self.expect("pass", self.script, args=["qa-down", str(self.tmp / f"qa{n}.md")])


class State(HookCase):
    script = HOOKS / "state.py"

    def state(self, *lines):
        path = self.tmp / "state.md"
        L.write_text(path, "\n".join(lines) + "\n")
        return str(path)

    def test_tick_pause_and_drain(self):
        cases = [(("mode: pause-until " + iso(3600), "slot 1: free"), "deny", "paused until "),
                 (("mode: pause-until " + iso(-3600), "slot 1: free"), "pass", ""),
                 (("mode: drain", f"slot 1: #4 build 1 loop-builder since {iso(-60)} — {self.tmp}/r4",
                   "slot 2: free"), "deny", "draining"),
                 (("mode: drain", "slot 1: free", "slot 2: free"), "deny", "drained"),
                 (("slot 1: free",), "pass", "")]
        for lines, want, reason in cases:
            self.expect(want, self.script, args=["tick", self.state(*lines)])
            self.assertTrue(self.reason.startswith(reason), self.reason)

    def test_tick_marks_overdue_phase(self):
        (self.tmp / "r1").mkdir()
        (self.tmp / "r2").mkdir()
        s = self.state("mode: run", f"slot 1: #1 ship 2 loop-reviewer since {iso(-1200)} — {self.tmp}/r1",
                       f"slot 2: #2 build 1 loop-builder since {iso(-300)} — {self.tmp}/r2",
                       f"slot 3: #3 build 1 loop-builder done — {self.tmp}/r3")
        for _ in (1, 2):
            self.expect("pass", self.script, args=["tick", s])
        marked = [i for i, l in enumerate(L.lines(s), 1) if "\U0001F422" in l]
        self.assertEqual(marked, [2])
        self.assertTrue(L.lines(s)[1].endswith(" \U0001F422 20/15 min"))
        self.assertEqual(len(L.lines(self.tmp / "r1" / "slowness.md")), 1)
        self.assertFalse((self.tmp / "r2" / "slowness.md").exists())

    def test_tick_unreadable_time_errors(self):
        self.expect("error", self.script, args=["tick", self.state("mode: pause-until tomorrow")])

    def test_model_mismatch_stops(self):
        agents = self.tmp / ".claude" / "agents"
        agents.mkdir(parents=True)
        L.write_text(agents / "loop-orchestrator.md", "---\nname: loop-orchestrator\nmodel: claude-opus-5-5\n---\n")
        s = self.state("mode: run")
        self.expect("deny", self.script, args=["model", s, "claude-sonnet-5-5"])
        self.assertEqual(L.lines(s)[-1], "stopped: model — serving claude-sonnet-5-5, pinned claude-opus-5-5")
        s = self.state("mode: run")
        self.expect("pass", self.script, args=["model", s, "claude-opus-5-5"])
        self.assertEqual(L.read_text(s), "mode: run\n")

    def test_fresh_rereads_changed_only(self):
        import shutil
        skill = self.tmp / "skill"
        shutil.copytree(HOOKS.parent, skill, ignore=shutil.ignore_patterns("__pycache__"))
        fresh = skill / "hooks" / "state.py"
        env = {"CLAUDE_CODE_SESSION_ID": "f1"}
        self.expect("pass", fresh, args=["fresh"], env=env)
        self.expect("pass", fresh, args=["fresh"], env=env)
        old = time.time() - 7 * 86400
        for p in skill.rglob("*"):
            if p.is_file():
                os.utime(p, (old, old))
        os.utime(self.tmp / ".claude" / "run" / "loop-issues" / "f1.read", (old + 3600, old + 3600))
        (skill / "RENDEZVOUS.md").touch()
        self.expect("deny", fresh, args=["fresh"], env=env)
        self.assertEqual(Path(self.reason).resolve(), (skill / "RENDEZVOUS.md").resolve())
        self.expect("pass", fresh, args=["fresh"], env=env)

    def test_count_shows_counter(self):
        s = self.state("mode: run", "planned: 3 (+1)", "done: #1 ✅ merged rework", "done: #2 📝 drafted")
        self.expect("pass", self.script, args=["count", s])
        self.assertEqual(self.out.strip(), "Counter: 2 / 3 lots (+1 added)")

    def merged(self, reg, n, lot):
        self.expect("pass", self.script, args=["merged", str(self.tmp / reg), str(n), str(self.tmp / lot)])
        return self.out.strip()

    def test_registry(self):
        for lot, text in (("lot7", "## Unpaid findings\n- a.sh:3 — x — y\n\n## Autre\n- b.sh:1 — z — w\n"),
                          ("lot8", "## Unpaid findings\n- c.sh:5 — u — v\n")):
            (self.tmp / lot).mkdir()
            L.write_text(self.tmp / lot / ("ship-1.md" if lot == "lot7" else "ship-2.md"), text)
        self.merged("findings.md", 7, "lot7")
        self.merged("findings.md", 8, "lot8")
        self.assertEqual(L.lines(self.tmp / "findings.md"),
                         ["- [ ] #7 a.sh:3 — x — y", "merged #7", "- [ ] #8 c.sh:5 — u — v", "merged #8"])
        L.write_text(self.tmp / "closed.md", "- [x] #7 a.sh:3 — x — y — absent @abc\n")
        for _ in (1, 2):
            self.merged("closed.md", 7, "lot7")
        entries = [l for l in L.lines(self.tmp / "closed.md") if l.startswith("- ")]
        self.assertEqual(len(entries), 1)
        self.assertNotIn("[ ]", entries[0])
        for _ in (1, 2):
            self.merged("open.md", 7, "lot7")
        self.assertEqual(len([l for l in L.lines(self.tmp / "open.md") if l.startswith("- ")]), 1)
        L.write_text(self.tmp / "longer.md", "- [x] #7 a.sh:3 — x — y — z — absent @abc\n")
        self.merged("longer.md", 7, "lot7")
        self.assertIn("- [ ] #7 a.sh:3 — x — y", L.lines(self.tmp / "longer.md"))

    def test_audit_due_every_ten(self):
        (self.tmp / "empty").mkdir()
        due = [i for i in range(1, 12) if self.merged("cadence.md", i, "empty")]
        self.assertEqual(due, [10, 11])
        with open(self.tmp / "cadence.md", "a", encoding="utf-8") as f:
            f.write("audited\n")
        due = [i for i in range(12, 22) if self.merged("cadence.md", i, "empty")]
        self.assertEqual(due, [21])


def spawn(agent, prompt):
    return json.dumps({"tool_input": {"subagent_type": agent, "prompt": prompt}})


class SpawnGuard(HookCase):
    script = HOOKS / "spawn_guard.py"

    def test_profile_gates(self):
        env = {"LOOP_PROFILE": str(PROFILE)}
        for p in ["run cargo check -p member", "then `cargo nextest run -p billing`", "guards: -p api -E x",
                  "run ci/lib/comply-workspace", "pnpm -C apps/webapp check"]:
            self.expect("deny", self.script, spawn("loop-builder", p), env=env)
        for p in ["Report dir: /r/issue-1 — files: comply-triage.md, pack-1.md",
                  "cargo via mbx, CARGO_TARGET_DIR unset; touched crates: api-key, member"]:
            self.expect("pass", self.script, spawn("loop-builder", p), env=env)
        self.expect("pass", self.script, spawn("loop-mechanic", "cargo check --workspace --all-targets"), env=env)
        self.expect("deny", self.script, spawn("skillhead:loop-builder", "run cargo check -p member"), env=env)
        self.expect("pass", self.script, spawn("skillhead:loop-mechanic", "cargo check --workspace"), env=env)

    def test_generic_defaults(self):
        for p in ["run `pytest -q` first", "then npm run lint", "go test ./...", "./gradlew test",
                  "pnpm --filter web test", "dotnet test"]:
            self.expect("deny", self.script, spawn("loop-shipper", p))
        for p in ["Report dir: /r/issue-1", "touched: src/test_utils.py, docs/testing.md"]:
            self.expect("pass", self.script, spawn("loop-shipper", p))

    def test_repo_profile_is_found_from_cwd(self):
        repo = self.tmp / "repo"
        (repo / ".claude").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        L.write_text(repo / ".claude" / "loop-issues.json", '{"gate_patterns_extra": ["\\\\bmake +ci\\\\b"]}')
        data = json.loads(spawn("loop-builder", "then make ci"))
        data["cwd"] = str(repo)
        self.expect("deny", self.script, json.dumps(data))
        data["cwd"] = str(self.tmp)
        self.expect("pass", self.script, json.dumps(data))


class BuilderNoTests(HookCase):
    script = HOOKS / "builder_no_tests.py"

    def test_profile(self):
        env = {"LOOP_PROFILE": str(PROFILE)}
        for c in ["cargo t", "cd x && cargo nextest run -p billing", 'bash -c "pnpm -C apps/webapp test"',
                  "ci/check", "cargo nextest run -p api -E 'binary(/_unit$/) | all()'"]:
            self.expect("deny", self.script, self.command(c, agent="skillhead:loop-builder"), env=env)
        for c in ["cargo nextest run -p api -E 'binary(/_unit$/)' 2>&1 | tail -40",
                  "cargo check -p x --all-targets", "cargo fmt --all"]:
            self.expect("pass", self.script, self.command(c, agent="skillhead:loop-builder"), env=env)

    def test_generic_defaults(self):
        for c in ["pytest -x", "python -m pytest", "npm test", "yarn run test", "go test ./...", "mvn verify",
                  "make test", "npx vitest run"]:
            self.expect("deny", self.script, self.command(c, agent="loop-builder"))
        for c in ["git status", "npm run build", "cargo build", "ls tests/", "go build ./..."]:
            self.expect("pass", self.script, self.command(c, agent="loop-builder"))

    def test_other_agents_may_test(self):
        for agent in (None, "skillhead:loop-mechanic", "general-purpose"):
            self.expect("pass", self.script, self.command("pytest -x", agent=agent))


if __name__ == "__main__":
    unittest.main(verbosity=1)
