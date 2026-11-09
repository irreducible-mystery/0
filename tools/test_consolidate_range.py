"""A push of several commits is checked and reverted as one landing.

Checking only the newest commit lets a tamper in an earlier commit of the same push survive,
because the newest commit alone can be clean. These tests build real repositories and exercise
the range base and the range revert without a network or a remote.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import consolidate  # noqa: E402

FIRST = "### 2026-01-01 00:00 UTC \u00b7 a \u00b7 note\n\nfirst\n"
TAMPER = "### 2026-01-01 00:00 UTC \u00b7 a \u00b7 note\n\nTAMPERED\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


class RangeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = pathlib.Path(temporary.name)
        env = patch.dict(os.environ, {**IDENTITY, "BEFORE_SHA": ""})
        env.start()
        self.addCleanup(env.stop)
        self.git("init", "-q", "-b", "main")
        (self.repo / "entries").mkdir()
        self.write("entries/20260101-000000-a.md", FIRST)
        self.write("README.md", "base\n")
        self.commit("base")
        self.base = self.rev("HEAD")

    def git(self, *args: str, check_: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.repo, check=check_, capture_output=True, text=True)

    def rev(self, name: str) -> str:
        return self.git("rev-parse", name).stdout.strip()

    def write(self, name: str, text: str) -> None:
        (self.repo / name).write_text(text, encoding="utf-8")

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def two_commit_push(self) -> str:
        self.write("entries/20260101-000000-a.md", TAMPER)
        self.commit("tamper with an entry")
        self.write("unrelated.txt", "x\n")
        self.commit("add an unrelated file")
        return self.rev("HEAD")

    def test_newest_commit_alone_is_clean_but_the_range_is_not(self):
        """The hole: the second commit is clean, so checking it alone accepts the push."""
        head = self.two_commit_push()
        self.assertTrue(consolidate.check.evaluate("HEAD~1", head, cwd=self.repo)["ok"])
        result = consolidate.check.evaluate(self.base, head, cwd=self.repo)
        self.assertFalse(result["ok"])
        self.assertTrue(any("modified" in p for p in result["problems"]))

    def test_revert_range_undoes_the_whole_push(self):
        head = self.two_commit_push()
        ok, err = consolidate.revert_range(self.base, head, cwd=self.repo)
        self.assertTrue(ok, err)
        self.assertEqual((self.repo / "entries/20260101-000000-a.md").read_text(encoding="utf-8"), FIRST)
        self.assertFalse((self.repo / "unrelated.txt").exists())
        self.assertEqual(self.rev("HEAD~1"), head, "the revert is one new commit on top of the push")
        self.assertTrue(self.git("log", "-1", "--format=%s").stdout.startswith("Revert the push"))
        self.assertTrue(consolidate.check.evaluate(self.base, "HEAD", cwd=self.repo)["ok"])

    def test_revert_range_handles_a_single_commit(self):
        self.write("entries/20260101-000000-a.md", TAMPER)
        self.commit("tamper")
        head = self.rev("HEAD")
        ok, err = consolidate.revert_range(self.base, head, cwd=self.repo)
        self.assertTrue(ok, err)
        self.assertEqual((self.repo / "entries/20260101-000000-a.md").read_text(encoding="utf-8"), FIRST)
        self.assertTrue(self.git("log", "-1", "--format=%s").stdout.startswith("Revert the push"))

    def test_push_base_prefers_an_ancestor_before(self):
        head = self.two_commit_push()
        with patch.dict(os.environ, {"BEFORE_SHA": self.base}):
            self.assertEqual(consolidate.push_base(head, [self.rev("HEAD~1")], cwd=self.repo), self.base)

    def test_push_base_ignores_all_zero_before(self):
        head = self.two_commit_push()
        with patch.dict(os.environ, {"BEFORE_SHA": "0" * 40}):
            self.assertEqual(consolidate.push_base(head, [self.rev("HEAD~1")], cwd=self.repo), self.rev("HEAD~1"))

    def test_push_base_ignores_a_before_that_is_not_an_ancestor(self):
        head = self.two_commit_push()
        tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
        stranger = self.git("commit-tree", tree, "-m", "not in this history").stdout.strip()
        with patch.dict(os.environ, {"BEFORE_SHA": stranger}):
            self.assertEqual(consolidate.push_base(head, [self.rev("HEAD~1")], cwd=self.repo), self.rev("HEAD~1"))

    def test_push_base_falls_back_to_the_last_consolidation_marker(self):
        """Without BEFORE_SHA, the landing starts after the last bot `trail:` commit."""
        self.write("TRAIL.md", "trail\n")
        with patch.dict(os.environ, {"GIT_AUTHOR_NAME": consolidate.BOT, "GIT_COMMITTER_NAME": consolidate.BOT}):
            self.commit("trail: 1 entries")
        marker = self.rev("HEAD")
        head = self.two_commit_push()
        self.assertEqual(consolidate.push_base(head, [self.rev("HEAD~1")], cwd=self.repo), marker)
        # and the range from the marker is red, though the newest commit alone is clean
        self.assertTrue(consolidate.check.evaluate("HEAD~1", head, cwd=self.repo)["ok"])
        self.assertFalse(consolidate.check.evaluate(marker, head, cwd=self.repo)["ok"])


if __name__ == "__main__":
    unittest.main()
