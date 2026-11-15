"""An entry's filename and heading are ASCII digits in a fixed shape, and end where they end: a name
that merely looks right, with digits from another script or a line break at the end, is not one."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assemble  # noqa: E402
import check  # noqa: E402
import entry  # noqa: E402

TEXT = "### 2026-01-01 00:00 UTC · a · note\n\nreal\n"
LOOKALIKE_NAMES = {
    "a line break at the end": "20260101-000000-a.md\n",
    "fullwidth digits": "２０２６０１０１-000000-a.md",
    "arabic-indic digits": "٢٠٢٦٠١٠١-000000-a.md",
    "devanagari digits": "२०२६०१०१-000000-a.md",
    "a carriage return at the end": "20260101-000000-a.md\r",
}
LOOKALIKE_HEADINGS = {
    "fullwidth digits in the date": "### ２０２６-01-01 00:00 UTC · a · note",
    "arabic-indic digits in the time": "### 2026-01-01 ٠٠:٠٠ UTC · a · note",
    "a line break at the end": "### 2026-01-01 00:00 UTC · a · note\n",
}


class RuleTests(unittest.TestCase):
    def test_a_real_name_and_heading_still_match(self):
        fname, content = entry.build("a", "note", "real", entry.dt.datetime(2026, 1, 1, tzinfo=entry.dt.timezone.utc))
        self.assertTrue(entry.NAME_RE.match(fname))
        self.assertTrue(entry.HEADING_RE.match(content.split("\n", 1)[0]))
        self.assertTrue(entry.NAME_RE.match("20260101-000000-a-b-9.md"))

    def test_lookalike_names_do_not_match(self):
        for what, name in LOOKALIKE_NAMES.items():
            self.assertIsNone(entry.NAME_RE.match(name), what)

    def test_lookalike_headings_do_not_match(self):
        for what, heading in LOOKALIKE_HEADINGS.items():
            self.assertIsNone(entry.HEADING_RE.match(heading), what)


class CheckTests(unittest.TestCase):
    """Through the checker: such a file reaches the filename rule as its literal name and is refused,
    rather than slipping through as an entries-only addition."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = pathlib.Path(tmp.name)
        identity = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        env = patch.dict(os.environ, identity)
        env.start()
        self.addCleanup(env.stop)
        self.git("init", "-q", "-b", "main")
        (self.repo / "entries").mkdir()
        (self.repo / "entries" / "20260101-000000-a.md").write_text(TEXT, encoding="utf-8")
        self.commit("first entry")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, encoding="utf-8").stdout

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def test_a_lookalike_filename_is_refused_not_merged(self):
        for what, name in LOOKALIKE_NAMES.items():
            self.git("checkout", "-qb", f"b{len(what)}-{abs(hash(what))}", "main")
            (self.repo / "entries" / name.replace("a.md", "b.md")).write_text(TEXT, encoding="utf-8")
            self.commit(what)
            result = check.evaluate("main", "HEAD", self.repo)
            self.assertFalse(result["ok"], what)
            self.assertFalse(result["entries_only"], what)
            self.assertEqual(result["other_changes"], 0, what)
            self.assertTrue(any("filename must be" in p for p in result["problems"]), (what, result["problems"]))
            self.git("checkout", "-q", "main")

    def test_a_lookalike_heading_is_refused(self):
        heading = LOOKALIKE_HEADINGS["fullwidth digits in the date"]
        (self.repo / "entries" / "20260102-000000-b.md").write_text(heading + "\n\nreal\n", encoding="utf-8")
        self.commit("lookalike heading")
        result = check.evaluate("main~1", "main", self.repo)
        self.assertFalse(result["ok"])
        self.assertTrue(any("first line must be" in p for p in result["problems"]), result["problems"])


class AssembleTests(unittest.TestCase):
    def test_assembly_refuses_lookalikes(self):
        for what, name in LOOKALIKE_NAMES.items():
            with tempfile.TemporaryDirectory() as d:
                (pathlib.Path(d) / name).write_text(TEXT, encoding="utf-8")
                with self.assertRaises(ValueError, msg=what):
                    assemble.entries(pathlib.Path(d))
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "20260101-000000-a.md").write_text(LOOKALIKE_HEADINGS["fullwidth digits in the date"] + "\n\nreal\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                assemble.entries(pathlib.Path(d))


if __name__ == "__main__":
    unittest.main()
