#!/usr/bin/env python3
"""Checks skills/initialize/new_project.py and the template: python3 templates/test_template.py"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]


def generate(target, *args):
    return subprocess.run([sys.executable, str(REPO / "skills" / "initialize" / "new_project.py"), str(target), *args],
                          capture_output=True, text=True, encoding="utf-8")


class Template(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_fresh_project_is_green(self):
        for forge in ("github", "gitlab"):
            target = self.tmp / forge
            self.assertEqual(generate(target, "--name", "Démo", "--forge", forge, "--mode", "automerge").returncode, 0)
            leftovers = [p for p in target.rglob("*") if p.is_file() and ".git" not in p.parts
                         and "{{" in p.read_text(encoding="utf-8", errors="ignore")]
            self.assertEqual(leftovers, [], "placeholders left")
            self.assertIn("loop-issues: automerge", (target / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertEqual((target / ".github").exists(), forge == "github")
            self.assertEqual((target / ".gitlab-ci.yml").exists(), forge == "gitlab")
            check = subprocess.run([sys.executable, str(target / "ci" / "check.py")], cwd=target,
                                   capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_existing_files_are_never_overwritten(self):
        target = self.tmp / "old"
        target.mkdir()
        (target / "README.md").write_text("# Mine\n", encoding="utf-8")
        result = generate(target)
        self.assertEqual(result.returncode, 0)
        self.assertEqual((target / "README.md").read_text(encoding="utf-8"), "# Mine\n")
        self.assertIn("README.md", result.stdout)
        self.assertFalse((target / ".git").exists(), "no git init in an existing directory")

    def test_dry_run_changes_nothing(self):
        target = self.tmp / "dry"
        target.mkdir()
        (target / "README.md").write_text("# Mine\n", encoding="utf-8")
        result = generate(target, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([p.name for p in target.iterdir()], ["README.md"], "dry run wrote files")
        self.assertIn("+ CLAUDE.md", result.stdout)
        self.assertIn("README.md", result.stdout.split("Already present")[1])

    def test_guards_catch_a_dated_rule(self):
        target = self.tmp / "dated"
        generate(target, "--no-git")
        with open(target / "PRODUCT.md", "a", encoding="utf-8") as f:
            f.write("- Changed on 16/09/2026, see #12.\n")
        check = subprocess.run([sys.executable, str(target / "ci" / "check.py"), "--guards"], cwd=target,
                               capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(check.returncode, 1)
        self.assertIn("PRODUCT.md", check.stdout + check.stderr)


if __name__ == "__main__":
    unittest.main()
