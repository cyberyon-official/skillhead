#!/usr/bin/env python3
"""The loop's written contracts match the code that reads them.

  STATE.md     its example parses with state.py (tick, count) line for line
  SKILL.md     every agent of § Agents is a file of agents/, with a budget
  briefs       every `FILE.md § Heading` reference names an existing heading
"""
import re
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

sys.dont_write_bytecode = True
HOOKS = Path(__file__).resolve().parent
SKILL = HOOKS.parent
PLUGIN = SKILL.parents[1]
sys.path.insert(0, str(HOOKS))
import _lib as L  # noqa: E402
import state  # noqa: E402


def example_lines():
    text = (SKILL / "STATE.md").read_text(encoding="utf-8")
    block = text[text.index("## Example"):]
    return block.split("```")[1].strip("\n").splitlines()


class StateSpec(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_every_example_line_is_a_documented_kind(self):
        text = (SKILL / "STATE.md").read_text(encoding="utf-8")
        kinds = set(re.findall(r"^\| `([a-z]+)[: ]", text, re.M))
        for line in example_lines():
            self.assertIn(line.split(":")[0].split(" ")[0], kinds, line)

    def test_tick_reads_the_example_slots(self):
        lines = example_lines()
        busy = [l for l in lines if " since " in l]
        self.assertTrue(busy, "the example shows a running phase")
        for line in busy:
            self.assertIsNotNone(state.SLOT.match(line), f"tick cannot read: {line}")
        # A phase started long ago is marked over budget, with its plugin-scoped agent.
        old = (L.now() - timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        path = self.tmp / "state.md"
        L.write_text(path, "\n".join(re.sub(r"since \S+", f"since {old}", l) for l in lines) + "\n")
        (self.tmp / "r").mkdir()
        L.write_text(path, L.read_text(path).replace("/r/issue-42", str(self.tmp / "r")))
        state.tick(str(path))
        self.assertIn("\U0001F422", L.read_text(path), "an overdue phase is not marked")

    def test_count_reads_the_example(self):
        path = self.tmp / "state.md"
        L.write_text(path, "\n".join(example_lines()) + "\n")
        self.assertIsNone(state.count(str(path)))


class AgentsTable(unittest.TestCase):
    def test_every_agent_row_has_a_file_and_a_budget_or_none(self):
        rows = re.findall(r"^\|[^|]*\| `(?:skillhead:)?([a-z-]+)` \|", (SKILL / "SKILL.md").read_text(encoding="utf-8"), re.M)
        self.assertTrue(rows, "no agent rows in SKILL.md § Agents")
        files = {p.stem for p in (PLUGIN / "agents").glob("*.md")}
        for name in rows:
            self.assertIn(name, files, f"SKILL.md names agent {name}, agents/ has no {name}.md")
        self.assertGreater(state.budget("skillhead:loop-builder"), 0)
        self.assertEqual(state.budget("skillhead:loop-builder"), state.budget("loop-builder"))


class SectionReferences(unittest.TestCase):
    REF = re.compile(r"\b([A-Z][A-Z-]*\.md) § ([^\s,.;)`]+(?: [^\s,.;)`]+)?)")

    def headings(self, path):
        """Heading titles; a phase heading (`## Phase `close` — …`) is also its phase name."""
        titles = []
        for h in re.findall(r"^#{2,3} .+$", path.read_text(encoding="utf-8"), re.M):
            title = re.sub(r"^#+\s*", "", h).strip().lower()
            titles.append(title)
            phase = re.match(r"phase `([a-z-]+)", title)
            if phase:
                titles.append(phase.group(1))
        return titles

    def test_cross_file_references_resolve(self):
        broken = []
        for source in list(SKILL.glob("*.md")) + list((PLUGIN / "agents").glob("*.md")):
            for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
                for name, ref in self.REF.findall(line):
                    target = SKILL / name
                    if not target.exists():
                        continue
                    first = ref.split()[0].lower()
                    if not any(h == ref.lower() or h.startswith(ref.lower()) or h.split()[0] == first or
                               ref.lower().startswith(h) for h in self.headings(target)):
                        broken.append(f"{source.name}:{number}: {name} § {ref}")
        self.assertFalse(broken, "references to missing headings:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main()
