"""A push of several commits is checked and reverted as one landing.

Checking only the newest commit lets a tamper in an earlier commit of the same push survive,
because the newest commit alone can be clean. These tests build real repositories and exercise
the range base and the range revert without a network or a remote.
"""
from __future__ import annotations

import os
import pathlib
import shutil
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

    def test_push_base_refuses_a_before_that_is_not_an_ancestor(self):
        head = self.two_commit_push()
        tree = self.git("rev-parse", "HEAD^{tree}").stdout.strip()
        stranger = self.git("commit-tree", tree, "-m", "not in this history").stdout.strip()
        with patch.dict(os.environ, {"BEFORE_SHA": stranger}):
            with self.assertRaises(ValueError):
                consolidate.push_base(head, [self.rev("HEAD~1")], cwd=self.repo)

    def test_a_marker_does_not_make_an_accepted_change_part_of_the_next_push(self):
        self.write("TRAIL.md", "trail\n")
        with patch.dict(os.environ, {"GIT_AUTHOR_NAME": consolidate.BOT, "GIT_COMMITTER_NAME": consolidate.BOT}):
            self.commit("trail: 1 entries")
        self.write("accepted.txt", "keep this\n")
        self.commit("accepted code-only landing")
        accepted = self.rev("HEAD")
        self.write("entries/20260101-000000-a.md", TAMPER)
        self.commit("tamper later")
        head = self.rev("HEAD")
        base = consolidate.push_base(head, [accepted], cwd=self.repo)
        self.assertEqual(base, accepted)
        ok, err = consolidate.revert_range(base, head, cwd=self.repo)
        self.assertTrue(ok, err)
        self.assertEqual((self.repo / "accepted.txt").read_text(), "keep this\n")

    def test_a_merge_is_reverted_once_even_when_its_branch_edits_a_file_twice(self):
        self.git("checkout", "-qb", "feature")
        self.write("entries/20260101-000000-a.md", TAMPER)
        self.commit("first edit")
        self.write("entries/20260101-000000-a.md", TAMPER + "again\n")
        self.commit("second edit")
        feature = self.rev("HEAD")
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "-m", "merge feature", "feature")
        head = self.rev("HEAD")
        with patch.dict(os.environ, {"BEFORE_SHA": feature}):
            with self.assertRaises(ValueError):
                consolidate.push_base(head, [self.base, feature], cwd=self.repo)
        ok, err = consolidate.revert_range(self.base, head, cwd=self.repo)
        self.assertTrue(ok, err)
        self.assertEqual(self.rev("HEAD^{tree}"), self.rev(self.base + "^{tree}"))
        self.assertEqual(self.rev("HEAD^"), head)

    def test_a_later_writer_is_not_included_in_an_old_rollback(self):
        head = self.two_commit_push()
        self.write("later.txt", "someone else's accepted work\n")
        self.commit("later writer")
        tip = self.rev("HEAD")
        ok, err = consolidate.revert_range(self.base, head, cwd=self.repo)
        self.assertFalse(ok)
        self.assertIn("moved", err)
        self.assertEqual(self.rev("HEAD"), tip)
        self.assertTrue((self.repo / "later.txt").exists())

    def test_dirty_checkout_is_left_untouched(self):
        head = self.two_commit_push()
        self.write("README.md", "local work\n")
        ok, err = consolidate.revert_range(self.base, head, cwd=self.repo)
        self.assertFalse(ok)
        self.assertIn("clean", err)
        self.assertEqual((self.repo / "README.md").read_text(), "local work\n")

    def test_untracked_test_artifacts_survive_a_rollback(self):
        head = self.two_commit_push()
        self.write("test-output.txt", "keep this artifact\n")
        ok, err = consolidate.revert_range(self.base, head, cwd=self.repo)
        self.assertTrue(ok, err)
        self.assertEqual((self.repo / "test-output.txt").read_text(), "keep this artifact\n")

    def prepare_landing(self):
        """Real consolidate subprocess, local remote, no GitHub calls or live tests."""
        source = pathlib.Path(__file__).resolve().parent
        (self.repo / "tools").mkdir()
        for name in ("consolidate.py", "check.py", "entry.py", "assemble.py"):
            shutil.copy(source / name, self.repo / "tools" / name)
        self.write(".gitignore", "__pycache__/\n")
        (self.repo / "tools/test_stub.py").write_text("import unittest\nclass Smoke(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n")
        self.commit("install the tools under test")
        base = self.rev("HEAD")
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.stub_bin = pathlib.Path(temp.name) / "bin"
        self.stub_bin.mkdir()
        stub = self.stub_bin / "gh"
        stub.write_text("#!/bin/sh\nexit 0\n")
        stub.chmod(0o755)
        remote = pathlib.Path(temp.name) / "remote.git"
        self.git("init", "-q", "--bare", str(remote))
        self.git("remote", "add", "origin", str(remote))
        return base

    def consolidate_landing(self, before, after):
        self.git("push", "-q", "origin", "HEAD:main")
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("GH_", "GITHUB_", "ACTIONS_"))}
        env.update(BEFORE_SHA=before, AFTER_SHA=after)
        env["PATH"] = str(self.stub_bin) + os.pathsep + env.get("PATH", "")
        return subprocess.run([sys.executable, "tools/consolidate.py"], cwd=self.repo,
                              env=env, capture_output=True, text=True, timeout=30)

    def test_workflow_boundaries_revert_the_entire_push_in_a_real_remote(self):
        base = self.prepare_landing()
        head = self.two_commit_push()
        result = self.consolidate_landing(base, head)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.rev("origin/main^{tree}"), self.rev(base + "^{tree}"))
        self.assertEqual(self.rev("origin/main^"), head)

    def test_delayed_workflow_refuses_to_widen_its_boundary(self):
        base = self.prepare_landing()
        head = self.two_commit_push()
        self.write("later.txt", "keep the later writer\n")
        self.commit("later landing")
        tip = self.rev("HEAD")
        result = self.consolidate_landing(base, head)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("main moved beyond landing", result.stdout)
        self.assertEqual(self.rev("origin/main"), tip)

    def test_a_landing_with_failing_tests_is_reverted(self):
        base = self.prepare_landing()
        self.write("tools/test_stub.py", "import unittest\nclass Red(unittest.TestCase):\n def test_red(self): self.fail('probe')\n")
        self.commit("a failing test")
        head = self.rev("HEAD")
        result = self.consolidate_landing(base, head)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.rev("origin/main^{tree}"), self.rev(base + "^{tree}"))

    def test_a_good_landing_is_kept_and_the_trail_is_regenerated(self):
        base = self.prepare_landing()
        self.write("accepted.txt", "good landing\n")
        self.commit("a good landing")
        head = self.rev("HEAD")
        result = self.consolidate_landing(base, head)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("good landing", self.git("show", "origin/main:accepted.txt").stdout)
        self.assertIn("first", self.git("show", "origin/main:TRAIL.md").stdout)

    def test_before_without_after_cannot_broaden_a_manual_run(self):
        base = self.prepare_landing()
        head = self.two_commit_push()
        result = self.consolidate_landing(base, "")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("requires AFTER_SHA", result.stdout)
        self.assertEqual(self.rev("origin/main"), head)

    def test_push_workflow_supplies_both_boundaries(self):
        workflow = pathlib.Path(__file__).resolve().parent.parent / ".github/workflows/main.yml"
        text = workflow.read_text()
        self.assertIn("BEFORE_SHA: ${{ github.event.before }}", text)
        self.assertIn("AFTER_SHA: ${{ github.event.after }}", text)


if __name__ == "__main__":
    unittest.main()
