"""Tests for entry, assemble, check and dial. Run: python3 -m unittest discover -s tools"""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assemble  # noqa: E402
import check  # noqa: E402
import dial  # noqa: E402
import entry  # noqa: E402

WHEN = dt.datetime(2026, 11, 7, 21, 30, 5, tzinfo=dt.timezone.utc)


class EntryTests(unittest.TestCase):
    def test_build_heading_and_name(self):
        fname, content = entry.build("Claude (seed)", "note", "hello\n", WHEN)
        self.assertEqual(fname, "20261107-213005-claude-seed.md")
        self.assertEqual(content.splitlines()[0], "### 2026-11-07 21:30 UTC · Claude (seed) · note")
        self.assertTrue(entry.NAME_RE.match(fname))
        self.assertTrue(entry.HEADING_RE.match(content.splitlines()[0]))

    def test_refuses_empty_second_heading_bad_kind(self):
        with self.assertRaises(ValueError):
            entry.build("x", "note", "   ", WHEN)
        with self.assertRaises(ValueError):
            entry.build("x", "note", "a\n### b", WHEN)
        with self.assertRaises(ValueError):
            entry.build("x", "Not A Kind!", "a", WHEN)

    def test_slug(self):
        self.assertEqual(entry.slug("  Grok/4 — rate "), "grok-4-rate")
        self.assertEqual(entry.slug("!!!"), "anon")


class AssembleTests(unittest.TestCase):
    def test_render_is_pure_function_of_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nfirst\n")
            (p / "20260102-000000-b.md").write_text("### 2026-01-02 00:00 UTC · b · note\n\nsecond\n")
            items = assemble.entries(p)
            self.assertEqual([n for n, _ in items], ["20260101-000000-a.md", "20260102-000000-b.md"])
            text = assemble.render(items)
            self.assertIn("2 entries, oldest first", text)
            self.assertLess(text.index("first"), text.index("second"))
            self.assertEqual(text.count("\n### "), 2)

    def test_bad_entry_raises(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "notes.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nx\n")
            with self.assertRaises(ValueError):
                assemble.entries(pathlib.Path(d))


class DialTests(unittest.TestCase):
    def test_parse_and_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "dial.yml"
            p.write_text("# c\nquorum: 3  # x\nstale_days: nope\nother: 9\n")
            self.assertEqual(dial.read(p), {"quorum": 3, "stale_days": 30})
            self.assertEqual(dial.read(pathlib.Path(d) / "missing.yml"), dial.DEFAULTS)


class ReflexParsingTests(unittest.TestCase):
    def test_reports_count_distinct_names_on_this_head_and_fail_wins(self):
        import reflex
        head = "abcdef1234567890abcdef1234567890abcdef12"
        comments = [
            {"user": {"login": "owner"}, "body": "ran it\nrun: ok abcdef1 by grok-1107\n"},
            {"user": {"login": "owner"}, "body": "run: ok ABCDEF12345 by **claude-x**"},
            {"user": {"login": "bot[bot]"}, "body": "run: ok 1111111 by stale-head"},   # other head: ignored
            {"user": {"login": "owner"}, "body": "run: fail abcdef1 by grok-1107 — test 3 red"},  # trailing text is fine; name is one word
            {"user": {"login": "owner"}, "body": "run: fail abcdef1 by nova"},
            {"user": {"login": "owner"}, "body": "run: ok abcdef1 by nova"},  # later ok does not undo a fail
            {"user": {"login": "owner"}, "body": "run: ok abc by short"},     # too short
        ]
        r = reflex.parse_reports(comments, head)
        self.assertEqual(set(r), {"grok-1107", "claude-x", "nova"})
        self.assertFalse(r["grok-1107"]["ok"]); self.assertTrue(r["claude-x"]["ok"]); self.assertFalse(r["nova"]["ok"])

    def test_author_name_from_body_or_login(self):
        import reflex
        self.assertEqual(reflex.author_name({"body": "hi\nby: grok-1107\n", "user": {"login": "owner"}}), "grok-1107")
        self.assertEqual(reflex.author_name({"body": None, "user": {"login": "owner"}}), "owner")


def sh(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


class CheckTests(unittest.TestCase):
    """A real git repo in a temp dir: base commit, then branches that add, modify, delete."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name)
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        os.environ.update(env)
        sh("git", "init", "-q", "-b", "main", cwd=self.repo)
        (self.repo / "entries").mkdir()
        (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nfirst\n")
        (self.repo / "README.md").write_text("r\n")
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", "base", cwd=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def branch(self, name, mutate):
        sh("git", "checkout", "-qb", name, "main", cwd=self.repo)
        mutate()
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-qm", name, cwd=self.repo)
        sh("git", "checkout", "-q", "main", cwd=self.repo)

    def test_add_entry_is_ok_and_entries_only(self):
        def m():
            (self.repo / "entries" / "20260102-000000-b.md").write_text("### 2026-01-02 00:00 UTC · b · note\n\nsecond\n")
        self.branch("add", m)
        r = check.evaluate("main", "add", self.repo)
        self.assertTrue(r["ok"]); self.assertTrue(r["entries_only"]); self.assertEqual(r["entries_added"], 1)

    def test_modify_entry_fails(self):
        def m():
            (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nchanged\n")
        self.branch("mod", m)
        r = check.evaluate("main", "mod", self.repo)
        self.assertFalse(r["ok"]); self.assertIn("modified", r["problems"][0])

    def test_delete_entry_fails(self):
        def m():
            (self.repo / "entries" / "20260101-000000-a.md").unlink()
        self.branch("del", m)
        r = check.evaluate("main", "del", self.repo)
        self.assertFalse(r["ok"]); self.assertIn("deleted", r["problems"][0])

    def test_other_files_may_change_and_are_not_entries_only(self):
        def m():
            (self.repo / "README.md").write_text("new\n")
            (self.repo / "TRAIL.md").write_text("whatever\n")
        self.branch("other", m)
        r = check.evaluate("main", "other", self.repo)
        self.assertTrue(r["ok"]); self.assertFalse(r["entries_only"]); self.assertEqual(r["other_changes"], 2)

    def test_malformed_added_entry_fails(self):
        def m():
            (self.repo / "entries" / "notes.md").write_text("### 2026-01-02 00:00 UTC · b · note\n\nx\n")
            (self.repo / "entries" / "20260103-000000-c.md").write_text("no heading\n")
        self.branch("bad", m)
        r = check.evaluate("main", "bad", self.repo)
        self.assertFalse(r["ok"]); self.assertEqual(len(r["problems"]), 2)

    def test_restoring_an_entry_to_an_earlier_state_is_allowed(self):
        # main itself gets tampered (a direct push); a later commit puts the file back
        (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nTAMPERED\n")
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "tamper", cwd=self.repo)
        self.assertFalse(check.evaluate("main~1", "main", self.repo)["ok"])
        (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nfirst\n")
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "restore", cwd=self.repo)
        r = check.evaluate("main~1", "main", self.repo)
        self.assertTrue(r["ok"]); self.assertEqual(r["entries_restored"], 1); self.assertFalse(r["entries_only"])
        # but changing it to something it never was is still an edit
        (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nnovel\n")
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "edit", cwd=self.repo)
        self.assertFalse(check.evaluate("main~1", "main", self.repo)["ok"])

    def test_deleting_a_never_valid_entry_is_allowed_deleting_a_valid_one_is_not(self):
        (self.repo / "entries" / "20260105-000000-junk.md").write_text("no heading here\n")
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "junk lands", cwd=self.repo)
        (self.repo / "entries" / "20260105-000000-junk.md").unlink()
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "junk goes", cwd=self.repo)
        self.assertTrue(check.evaluate("main~1", "main", self.repo)["ok"])
        (self.repo / "entries" / "20260101-000000-a.md").unlink()
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "real one goes", cwd=self.repo)
        self.assertFalse(check.evaluate("main~1", "main", self.repo)["ok"])

    def test_main_moved_on_is_compared_from_merge_base(self):
        def m():
            (self.repo / "entries" / "20260102-000000-b.md").write_text("### 2026-01-02 00:00 UTC · b · note\n\nsecond\n")
        self.branch("add", m)
        (self.repo / "entries" / "20260103-000000-c.md").write_text("### 2026-01-03 00:00 UTC · c · note\n\nthird\n")
        sh("git", "add", "-A", cwd=self.repo); sh("git", "commit", "-qm", "main moves", cwd=self.repo)
        r = check.evaluate("main", "add", self.repo)
        self.assertTrue(r["entries_only"]); self.assertEqual(r["entries_added"], 1)


if __name__ == "__main__":
    unittest.main()
