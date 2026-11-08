"""Quoted Git filenames must not hide files under entries/ from the checker."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check

TEXT = "### 2026-01-01 00:00 UTC · test · note\n\nA record.\n"


class DiffPathTests(unittest.TestCase):
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
        self.git("config", "core.quotePath", "true")
        (self.repo / "entries").mkdir()
        (self.repo / "README.md").write_text("A trail.\n", encoding="utf-8")
        self.commit("base")

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True,
            capture_output=True, encoding="utf-8",
        ).stdout

    def write(self, path, text=TEXT):
        (self.repo / path).write_text(text, encoding="utf-8")

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def test_quoted_entry_names_are_literal_and_rejected(self):
        paths = [
            "entries/20260101-000000-café.md",
            "entries/20260101-000000-a\tb.md",
            "entries/20260101-000000-a\nb.md",
            "entries/20260101-000000-a\rb.md",
            'entries/20260101-000000-a"b.md',
        ]
        for path in paths:
            self.write(path)
        self.commit("add names that Git would quote")
        changes = check.changes("HEAD~1", "HEAD", self.repo)
        self.assertEqual({path for _, path, _ in changes}, set(paths))
        result = check.evaluate("HEAD~1", "HEAD", self.repo)
        self.assertFalse(result["ok"])
        self.assertFalse(result["entries_only"])
        self.assertEqual(result["other_changes"], 0)
        self.assertEqual(len(result["problems"]), len(paths))

    def test_valid_addition_cannot_hide_an_invalid_quoted_addition(self):
        self.write("entries/20260101-000000-good.md")
        self.write("entries/20260101-000000-café.md")
        self.commit("one valid and one invalid entry name")
        result = check.evaluate("HEAD~1", "HEAD", self.repo)
        self.assertFalse(result["ok"])
        self.assertEqual(result["entries_added"], 1)
        self.assertEqual(result["other_changes"], 0)

    def test_quoted_destination_cannot_hide_a_rename_into_entries(self):
        self.write('draft-"quoted".md')
        self.commit("draft outside the trail")
        source = self.repo / 'draft-"quoted".md'
        target = self.repo / 'entries/20260101-000000-a"b.md'
        source.rename(target)
        self.commit("rename into the trail")
        self.assertEqual(check.changes("HEAD~1", "HEAD", self.repo), [
            ("R", source.name, str(target.relative_to(self.repo))),
        ])
        result = check.evaluate("HEAD~1", "HEAD", self.repo)
        self.assertFalse(result["ok"])
        self.assertEqual(result["other_changes"], 0)

    def test_quoted_source_cannot_hide_a_rename_out_of_entries(self):
        source = self.repo / 'entries/20260101-000000-a"b.md'
        self.write(str(source.relative_to(self.repo)))
        self.commit("an invalid name lands by direct push")
        target = self.repo / 'draft-"quoted".md'
        source.rename(target)
        self.commit("rename out of the trail")
        result = check.evaluate("HEAD~1", "HEAD", self.repo)
        self.assertFalse(result["ok"])
        self.assertEqual(result["other_changes"], 0)

    def test_quoted_unrelated_files_remain_other_changes(self):
        path = 'notes\t"café"\n.md'
        self.write(path, "Not a trail entry.\n")
        self.commit("other work")
        self.assertEqual(check.changes("HEAD~1", "HEAD", self.repo), [("A", path, None)])
        result = check.evaluate("HEAD~1", "HEAD", self.repo)
        self.assertTrue(result["ok"])
        self.assertFalse(result["entries_only"])
        self.assertEqual(result["other_changes"], 1)

    def test_non_utf8_entry_filename_is_rejected_without_a_decode_error(self):
        path = b"entries/20260101-000000-\xff.md"
        with open(os.fsencode(self.repo) + b"/" + path, "wb") as entry:
            entry.write(TEXT.encode("utf-8"))
        self.commit("a filename that is not UTF-8")
        result = check.evaluate("HEAD~1", "HEAD", self.repo)
        self.assertFalse(result["ok"])
        self.assertFalse(result["entries_only"])
        self.assertEqual(result["other_changes"], 0)
        self.assertEqual(len(result["problems"]), 1)


if __name__ == "__main__":
    unittest.main()
