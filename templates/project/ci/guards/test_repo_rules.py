"""Guards on the repo's own docs — the rules CLAUDE.md states, checked by machine."""
import re
import unittest

from _repo import ROOT, exists, files, path_like, prose_lines, read, rel

CLAUDE_MD_CEILING = 5000  # bytes

# Docs that hold rules: they speak in the present, history lives in Git.
RULE_DOCS = ["CLAUDE.md", "AGENTS.md", "CODING_STANDARDS.md", "CONTEXT.md", "PRODUCT.md", "DESIGN.md",
             "docs/agents/**/*.md", "docs/ux-writing/**/*.md", "docs/review-checklist.md",
             "docs/testing.md", "docs/tests-e2e.md"]
HISTORY = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "date"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"), "date"),
    (re.compile(r"(?<![\w&/])[#!]\d+\b"), "issue or MR number"),
    (re.compile(r"\b(MR|PR|merge request|pull request)\s*#?\d+\b", re.I), "MR number"),
]


class ClaudeMd(unittest.TestCase):
    def test_claude_md_ceiling(self):
        for name in ("CLAUDE.md", "AGENTS.md"):
            if exists(name):
                size = len(read(name).encode("utf-8"))
                self.assertLess(size, CLAUDE_MD_CEILING,
                                f"{name} is {size} bytes: move rules to the file its table points to")

    def test_pointers_resolve(self):
        missing = []
        for name in ("CLAUDE.md", "AGENTS.md", "CODING_STANDARDS.md"):
            if not exists(name):
                continue
            for number, line in prose_lines(read(name)):
                for span in re.findall(r"`([^`]+)`", line):
                    for token in span.split():
                        path = path_like(token)
                        if path and not exists(path):
                            missing.append(f"{name}:{number}: {path}")
        for path in files("**/*.md"):
            if ".git" in path.parts:
                continue
            for number, line in prose_lines(path.read_text(encoding="utf-8")):
                for target in re.findall(r"\]\(([^)#\s]+)", line):
                    if "://" not in target and not target.startswith("mailto:") \
                            and not (path.parent / target).exists():
                        missing.append(f"{rel(path)}:{number}: {target}")
        self.assertFalse(missing, "pointers to nothing:\n" + "\n".join(missing))


class RuleDocs(unittest.TestCase):
    def test_rules_have_no_history(self):
        found = []
        for path in files(*RULE_DOCS):
            for number, line in prose_lines(path.read_text(encoding="utf-8")):
                for pattern, kind in HISTORY:
                    m = pattern.search(line)
                    if m:
                        found.append(f"{rel(path)}:{number}: {kind} « {m.group(0)} »")
        self.assertFalse(found, "Git keeps the history, the rule speaks in the present:\n" + "\n".join(found))

    def test_standards_index_matches_guides(self):
        if not exists("CODING_STANDARDS.md"):
            self.skipTest("no CODING_STANDARDS.md")
        listed = set(re.findall(r"`(docs/agents/[^`]+\.md)`", read("CODING_STANDARDS.md")))
        present = {rel(p) for p in files("docs/agents/*.md")}
        self.assertEqual(sorted(present - listed), [], "guides missing from CODING_STANDARDS.md")
        self.assertEqual(sorted(listed - present), [], "CODING_STANDARDS.md lists missing guides")

    def test_review_checklist_is_numbered(self):
        if not exists("docs/review-checklist.md"):
            self.skipTest("no checklist")
        numbers = [int(m.group(1)) for _, line in prose_lines(read("docs/review-checklist.md"))
                   for m in [re.match(r"(\d+)\. ", line)] if m]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)),
                         "numbers are stable: retire a rule by striking it, never renumber")

    def test_glossary_terms_are_unique(self):
        if not exists("CONTEXT.md"):
            self.skipTest("no CONTEXT.md")
        terms = [m.group(1).strip().lower() for _, line in prose_lines(read("CONTEXT.md"))
                 for m in [re.match(r"\*\*(.+?)\*\*\s*:", line)] if m]
        duplicates = sorted({t for t in terms if terms.count(t) > 1})
        self.assertFalse(duplicates, f"one concept, one entry: {duplicates}")


class Adrs(unittest.TestCase):
    def test_adrs_are_indexed(self):
        adrs = [p for p in files("docs/adr/[0-9][0-9][0-9][0-9]-*.md") if not p.name.startswith("0000")]
        numbers = [int(p.name[:4]) for p in adrs]
        self.assertEqual(numbers, list(range(1, len(adrs) + 1)), "ADR numbers run from 0001 without gaps")
        index = read("docs/adr/README.md") if exists("docs/adr/README.md") else ""
        for path in adrs:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(f"# {path.name[:4]} "), f"{rel(path)}: title starts with its number")
            self.assertRegex(text, r"(?m)^Status: ", f"{rel(path)}: has a \"Status:\" line")
            self.assertIn(path.name, index, f"{rel(path)}: missing from docs/adr/README.md")


if __name__ == "__main__":
    unittest.main()
