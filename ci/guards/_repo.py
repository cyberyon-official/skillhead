"""Helpers for the guards: tests that read the repo itself, not the app.

A guard turns a rule written in the docs into a red test. Pattern of an
architecture test with explicit exceptions:

    from _repo import counted_sites, assert_listed_exactly

    # Every exception carries its reason in a comment.
    ALLOWED = ["src/legacy/url.py × 1"]  # migrated with the next billing change

    class UrlComposition(unittest.TestCase):
        def test_urls_are_composed_by_the_url_library(self):
            found = counted_sites(lambda text: text.count("rstrip('/')"), ["src/**/*.py"])
            assert_listed_exactly(self, found, ALLOWED)

A new occurrence, or an exception that no longer occurs, turns it red.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def exists(relative):
    return (ROOT / relative).exists()


def files(*globs):
    seen = []
    for pattern in globs:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.append(path)
    return seen


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def prose_lines(text):
    """(line number, line) outside fenced code blocks."""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def counted_sites(count, globs):
    """`path × n` for every file of globs where count(text) > 0."""
    found = []
    for path in files(*globs):
        n = count(path.read_text(encoding="utf-8", errors="replace"))
        if n:
            found.append(f"{rel(path)} × {n}")
    return found


def assert_listed_exactly(case, found, allowed):
    unexpected = sorted(set(found) - set(allowed))
    stale = sorted(set(allowed) - set(found))
    case.assertFalse(unexpected, f"new occurrences (fix them, or add an exception with its reason): {unexpected}")
    case.assertFalse(stale, f"exceptions that no longer occur (remove them): {stale}")


PATH_TOKEN = re.compile(r"^\.?[\w.-]+(/[\w.-]*)*$")


def path_like(token):
    token = token.strip(",;:()").rstrip(".")
    if not token or "://" in token or not PATH_TOKEN.match(token):
        return None
    if "/" in token or re.search(r"\.(md|json|py|ya?ml|toml)$", token):
        return token
    return None
