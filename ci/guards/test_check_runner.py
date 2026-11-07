"""The merge gate's own runner has its own test."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check  # noqa: E402


class Runner(unittest.TestCase):
    def run_steps(self, steps):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            red = check.run_steps(steps, cwd=tmp, out=out)
        return red, out.getvalue()

    def test_empty_step_is_skipped_and_said(self):
        red, out = self.run_steps([{"name": "lint", "run": ""}])
        self.assertEqual(red, [])
        self.assertIn("lint: no command", out)

    def test_green_and_red_steps(self):
        red, out = self.run_steps([{"name": "ok", "run": "exit 0"},
                                   {"name": "ko", "run": "echo boom && exit 3"}])
        self.assertEqual(red, ["ko"])
        self.assertIn("exit 3", out)
        self.assertIn("boom", out)

    def test_python_placeholder_is_this_interpreter(self):
        red, out = self.run_steps([{"name": "py", "run": "{python} -c \"import sys; sys.exit(0)\""}])
        self.assertEqual(red, [], out)

    def test_every_step_needs_a_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gates.json"
            path.write_text(json.dumps({"steps": [{"run": "true"}]}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                check.load_steps(path)

    def test_repo_gates_file_is_valid(self):
        check.load_steps(check.CI / "gates.json")


if __name__ == "__main__":
    unittest.main()
