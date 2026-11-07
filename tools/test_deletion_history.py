"""A damaged entry is not junk if a valid version exists in the base history."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402


class DeletionHistoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = pathlib.Path(tmp.name)
        identity = {
            "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        env = patch.dict(os.environ, identity)
        env.start()
        self.addCleanup(env.stop)
        self.git("init", "-q", "-b", "main")
        (self.repo / "entries").mkdir()
        self.entry = self.repo / "entries" / "20260101-000000-a.md"
        self.original = "### 2026-01-01 00:00 UTC \u00b7 a \u00b7 note\n\nfirst\n"
        self.entry.write_text(self.original, encoding="utf-8")
        self.commit("valid entry")

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True,
        ).stdout.strip()

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def assert_deletion_rejected(self, base: str = "main~1", head: str = "main") -> None:
        result = check.evaluate(base, head, self.repo)
        self.assertFalse(result["ok"])
        self.assertFalse(result["entries_only"])
        self.assertEqual(result["entries_restored"], 0)
        self.assertTrue(any("deleted" in p for p in result["problems"]))

    def test_previously_valid_entry_cannot_be_deleted_after_damage(self):
        self.entry.write_text("missing heading\n", encoding="utf-8")
        self.commit("damage")
        self.assertFalse(check.evaluate("main~1", "main", self.repo)["ok"])
        self.entry.unlink()
        self.commit("delete damaged entry")
        self.assert_deletion_rejected()

    def test_non_utf8_damage_does_not_erase_valid_history(self):
        self.entry.write_bytes(b"\xff\xfe\n")
        self.commit("non-UTF-8 damage")
        self.entry.unlink()
        self.commit("delete damaged entry")
        self.assert_deletion_rejected()

    def test_missing_path_at_advanced_base_does_not_erase_valid_history(self):
        self.git("checkout", "-qb", "delete")
        self.entry.unlink()
        self.commit("delete on branch")
        self.git("checkout", "-q", "main")
        self.entry.write_text("missing heading\n", encoding="utf-8")
        self.commit("damage on main")
        self.entry.unlink()
        self.commit("delete on main")
        self.assert_deletion_rejected("main", "delete")

    def test_multiple_never_valid_versions_can_still_be_cleaned_up(self):
        junk = self.repo / "entries" / "20260102-000000-junk.md"
        for text in ("missing heading\n", "still missing heading\n"):
            junk.write_text(text, encoding="utf-8")
            self.commit("junk version")
        junk.unlink()
        self.commit("remove junk")
        result = check.evaluate("main~1", "main", self.repo)
        self.assertTrue(result["ok"])
        self.assertEqual(result["entries_restored"], 1)
        self.assertFalse(result["entries_only"])

    def test_restoring_damaged_entry_remains_allowed(self):
        self.entry.write_text("missing heading\n", encoding="utf-8")
        self.commit("damage")
        self.entry.write_text(self.original, encoding="utf-8")
        self.commit("restore")
        result = check.evaluate("main~1", "main", self.repo)
        self.assertTrue(result["ok"])
        self.assertEqual(result["entries_restored"], 1)
        self.assertFalse(result["entries_only"])


if __name__ == "__main__":
    unittest.main()
