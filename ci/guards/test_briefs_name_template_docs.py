"""Every project document a brief sends an agent to is one the template creates.

The skills read a target repo's docs by path (`CONTEXT.md`,
`docs/review-checklist.md`, …); `templates/project/` is what lays those docs
down. A brief naming a path the template never creates sends its agent after
a file that does not exist. Scripts under `ci/` are the project's own gates,
not documents, and the stack profiles are examples: both are out of scope.
"""
import re
import unittest

from _repo import ROOT, files, rel

TEMPLATE = ROOT / "templates" / "project"
ROOT_DOCS = r"(?:CLAUDE|AGENTS|CODING_STANDARDS|CONTEXT|PRODUCT|DESIGN)\.md"
DOC_PATH = re.compile(r"`(docs/[\w./-]+|" + ROOT_DOCS + r"|\.claude/(?:skills/verify|loop-issues)[\w./-]*)`")
# A § or "section N" right after a path cites a part of that document.
SECTION = re.compile(r"`\)?\s*(§\s*\d+|section\s+\d+)", re.I)


def briefs():
    return [p for p in files("skills/**/*.md", "agents/*.md") if "profiles" not in p.parts]


class BriefsNameTemplateDocs(unittest.TestCase):
    def test_every_named_doc_exists_in_the_template(self):
        missing = []
        for path in briefs():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in DOC_PATH.finditer(line):
                    doc = m.group(1).rstrip("/")
                    if not (TEMPLATE / doc).exists():
                        missing.append(f"{rel(path)}:{number}: {m.group(1)}")
        self.assertFalse(missing, "briefs name project docs templates/project/ never creates:\n" + "\n".join(missing))

    def test_no_section_number_on_an_unnumbered_doc(self):
        orphans = []
        for path in briefs():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in DOC_PATH.finditer(line):
                    if not SECTION.match(line, m.end() - 1):
                        continue
                    doc = TEMPLATE / m.group(1).rstrip("/")
                    if doc.is_file() and not re.search(r"(?m)^#+\s*(§\s*)?\d+[.)]?\s", doc.read_text(encoding="utf-8")):
                        orphans.append(f"{rel(path)}:{number}: {m.group(0)}")
        self.assertFalse(orphans, "section cited in a document without numbered sections:\n" + "\n".join(orphans))


if __name__ == "__main__":
    unittest.main()
