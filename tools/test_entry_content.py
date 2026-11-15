"""Malformed entry content is a check failure, not a crashed checker."""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = pathlib.Path(__file__).resolve().parent
HEADING = "### 2026-01-01 00:00 UTC · test · note"


class EntryContentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = pathlib.Path(temporary.name)
        identity = patch.dict(os.environ, {
            "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        })
        identity.start()
        self.addCleanup(identity.stop)
        self.git("init", "-q", "-b", "main")
        (self.repo / "entries").mkdir()
        (self.repo / "tools").mkdir()
        for name in ("check.py", "entry.py"):
            shutil.copyfile(TOOLS / name, self.repo / "tools" / name)
        self.commit("base")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True,
            capture_output=True, encoding="utf-8",
        ).stdout

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def write(self, name, content):
        path = f"entries/20260101-000000-{name}.md"
        (self.repo / path).write_bytes(content)
        return path

    def run_check(self, *args):
        return subprocess.run(
            [sys.executable, "tools/check.py", "--base", "HEAD~1", "--head", "HEAD", *args],
            cwd=self.repo, capture_output=True, encoding="utf-8",
        )

    def json_result(self, expected_status):
        result = self.run_check("--json")
        self.assertEqual(result.returncode, expected_status, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_heading_only_and_whitespace_bodies_are_rejected(self):
        paths = [
            self.write(name, (HEADING + suffix).encode("utf-8"))
            for name, suffix in (("a", ""), ("b", "\n"), ("c", "\n\n \t\n"))
        ]
        self.commit("bodyless entries")
        result = self.json_result(1)
        self.assertFalse(result["ok"])
        self.assertFalse(result["entries_only"])
        self.assertCountEqual(result["problems"], [f"{path}: empty body" for path in paths])

    def test_invalid_utf8_does_not_stop_other_entry_checks(self):
        bad = self.write("a", (HEADING + "\n\n").encode("utf-8") + b"\xff\n")
        empty = self.write("b", (HEADING + "\n\n").encode("utf-8"))
        self.write("c", (HEADING + "\n\nA valid entry.\n").encode("utf-8"))
        self.commit("invalid bytes beside other entries")
        result = self.json_result(1)
        self.assertFalse(result["ok"])
        self.assertFalse(result["entries_only"])
        self.assertCountEqual(result["problems"], [
            f"{bad}: content must be UTF-8 text",
            f"{empty}: empty body",
        ])

    def test_unicode_body_without_final_newline_is_valid(self):
        self.write("a", (HEADING + "\n\ncafé — 雪").encode("utf-8"))
        self.commit("unicode entry")
        result = self.json_result(0)
        self.assertTrue(result["ok"])
        self.assertTrue(result["entries_only"])
        self.assertEqual(result["entries_added"], 1)
        self.assertEqual(result["problems"], [])

    def test_plain_output_reports_heading_only_entry(self):
        path = self.write("a", HEADING.encode("utf-8"))
        self.commit("heading without a body or newline")
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn(f"{path}: empty body", result.stdout)
        self.assertIn("NOT OK:", result.stdout)


if __name__ == "__main__":
    unittest.main()
