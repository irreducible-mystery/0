"""A restoration restores an entry to the first well-formed text it had on main, not to anything
else it has been."""
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

FIRST = "### 2026-01-01 00:00 UTC · a · note\n\nfirst\n"
TAMPER = "### 2026-01-01 00:00 UTC · a · note\n\nTAMPERED\n"  # well-formed, but not what was written
NOT_TEXT = b"\xff\xfe\n"  # not UTF-8


class RestorationTests(unittest.TestCase):
    """A real git repo in a temp dir. main holds one entry, written once; then things happen to it."""

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
        self.entry = self.repo / "entries" / "20260101-000000-a.md"
        self.commit(self.entry, FIRST, "first written")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True, encoding="utf-8").stdout.strip()

    def commit(self, path: pathlib.Path, content: str | bytes, message: str) -> None:
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def on_branch(self, name: str, path: pathlib.Path, content: str | bytes, message: str) -> None:
        """A branch off main's tip with one commit; main is checked out again afterwards."""
        self.git("checkout", "-qb", name, "main")
        self.commit(path, content, message)
        self.git("checkout", "-q", "main")

    def remove_on_branch(self, name: str, path: pathlib.Path) -> None:
        self.git("checkout", "-qb", name, "main")
        path.unlink()
        self.git("add", "-A")
        self.git("commit", "-qm", f"remove {path.name}")
        self.git("checkout", "-q", "main")

    def merge(self, branch: str) -> None:
        """Land a branch the way the reflex does: a merge commit on main, main as its first parent."""
        self.git("merge", "-q", "--no-ff", "--no-edit", branch)

    def assert_restoration(self, result: dict) -> None:
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["entries_restored"], 1)
        self.assertFalse(result["entries_only"])

    def assert_edit(self, result: dict) -> None:
        self.assertFalse(result["ok"])
        self.assertEqual(result["entries_restored"], 0)
        self.assertTrue(any("modified" in p for p in result["problems"]), result["problems"])

    def assert_tidying(self, result: dict) -> None:
        self.assertTrue(result["ok"], result["problems"])
        self.assertEqual(result["entries_restored"], 1)  # tidying is counted with restorations

    def test_putting_a_reverted_tamper_back_is_an_edit(self):
        # the hole: the tamper is in main's history, so the old rule called a return to it a restoration
        self.commit(self.entry, TAMPER, "tamper lands (a direct push)")
        self.commit(self.entry, FIRST, "the revert")
        self.on_branch("redo", self.entry, TAMPER, "put the tamper back")
        result = check.evaluate("main", "redo", self.repo)
        self.assert_edit(result)
        # and the refusal names the one text a restoration would go to
        first_blob = self.git("rev-parse", "main:entries/20260101-000000-a.md")[:7]
        self.assertIn(f"blob {first_blob}", result["problems"][0])

    def test_the_revert_itself_is_a_restoration(self):
        self.commit(self.entry, TAMPER, "tamper lands")
        self.assert_edit(check.evaluate("main~1", "main", self.repo))
        self.commit(self.entry, FIRST, "the revert")
        self.assert_restoration(check.evaluate("main~1", "main", self.repo))

    def test_a_branch_may_restore_what_main_still_has_wrong(self):
        self.commit(self.entry, TAMPER, "tamper lands and stays")
        self.on_branch("fix", self.entry, FIRST, "restore")
        self.assert_restoration(check.evaluate("main", "fix", self.repo))

    def test_after_two_tampers_only_the_first_text_is_restorable(self):
        other = "### 2026-01-01 00:00 UTC · a · note\n\nanother tamper\n"
        self.commit(self.entry, TAMPER, "tamper one")
        self.commit(self.entry, FIRST, "revert one")
        self.commit(self.entry, other, "tamper two")
        self.on_branch("to-first", self.entry, FIRST, "restore")
        self.on_branch("to-tamper-one", self.entry, TAMPER, "an earlier state, but not the first")
        self.assert_restoration(check.evaluate("main", "to-first", self.repo))
        self.assert_edit(check.evaluate("main", "to-tamper-one", self.repo))

    def test_a_draft_pushed_before_the_merge_is_not_the_original(self):
        # an author pushes a draft and then a fix; the reflex sees one addition and merges it. Only
        # the fix was ever on the trail: it is the original, and the draft cannot be "restored"
        entry = self.repo / "entries" / "20260102-000000-b.md"
        draft = "### 2026-01-02 00:00 UTC · b · note\n\na draft, with a tpyo\n"
        final = draft.replace("tpyo", "typo")
        self.git("checkout", "-qb", "pr", "main")
        self.commit(entry, draft, "the draft")
        self.commit(entry, final, "the fix")
        self.git("checkout", "-q", "main")
        self.assertTrue(check.evaluate("main", "pr", self.repo)["entries_only"])
        self.merge("pr")
        self.on_branch("to-draft", entry, draft, "back to the draft")
        self.assert_edit(check.evaluate("main", "to-draft", self.repo))
        self.commit(entry, final.replace("typo", "TAMPER"), "tamper lands")
        self.on_branch("restore", entry, final, "restore what the trail showed")
        self.assert_restoration(check.evaluate("main", "restore", self.repo))

    def test_a_pull_request_cannot_plant_the_original(self):
        # the author of a restoration branches from before the entry existed, puts a text of their
        # own into the branch's history, merges main into the branch (clean: both sides hold the same
        # bytes) and restores. The restoration is genuine and lands; the planted text was never on
        # main's own line, so it is no original
        entry = self.repo / "entries" / "20260102-000000-b.md"
        first = "### 2026-01-02 00:00 UTC · b · note\n\nfirst\n"
        tamper = first.replace("first", "TAMPERED")
        planted = first.replace("first", "planted")
        before = self.git("rev-parse", "main")
        self.commit(entry, first, "first written")
        self.commit(entry, tamper, "tamper lands")
        self.git("checkout", "-qb", "pr", before)
        self.commit(entry, planted, "plant")
        self.commit(entry, tamper, "the same bytes as main")
        self.git("merge", "-q", "--no-ff", "--no-edit", "main")  # the branch's own line is the first parent here
        self.commit(entry, first, "restore")
        self.git("checkout", "-q", "main")
        self.assert_restoration(check.evaluate("main", "pr", self.repo))
        self.merge("pr")
        self.on_branch("to-planted", entry, planted, "to the planted text")
        self.assert_edit(check.evaluate("main", "to-planted", self.repo))
        self.commit(entry, tamper, "tamper lands again")
        self.on_branch("restore-again", entry, first, "restore")
        self.assert_restoration(check.evaluate("main", "restore-again", self.repo))

    def test_a_landing_reverted_before_the_trail_showed_it_is_not_the_original(self):
        # an entry lands by merge and the merge is reverted (as consolidate does when main goes red),
        # so the trail never showed that text; the entry then lands again with other text. That
        # text is the original: the deletion on main's line started the path afresh
        entry = self.repo / "entries" / "20260102-000000-b.md"
        reverted = "### 2026-01-02 00:00 UTC · b · note\n\nlanded and reverted\n"
        shown = "### 2026-01-02 00:00 UTC · b · note\n\nlanded and kept\n"
        self.on_branch("first-landing", entry, reverted, "first landing")
        self.merge("first-landing")
        self.git("revert", "--no-edit", "-m", "1", "HEAD")
        self.on_branch("second-landing", entry, shown, "second landing")
        self.assertTrue(check.evaluate("main", "second-landing", self.repo)["entries_only"])
        self.merge("second-landing")
        self.on_branch("to-reverted", entry, reverted, "to the reverted text")
        self.assert_edit(check.evaluate("main", "to-reverted", self.repo))
        self.commit(entry, shown.replace("kept", "TAMPERED"), "tamper lands")
        self.on_branch("restore", entry, shown, "restore what the trail showed")
        self.assert_restoration(check.evaluate("main", "restore", self.repo))

    def test_the_original_is_the_first_well_formed_version(self):
        # a file that landed as junk and was later made well-formed counts from the well-formed text
        junk = self.repo / "entries" / "20260102-000000-j.md"
        valid = "### 2026-01-02 00:00 UTC · j · note\n\nreal\n"
        self.commit(junk, "no heading\n", "junk lands")
        self.commit(junk, valid, "made well-formed")
        self.commit(junk, valid.replace("real", "changed"), "tampered")
        self.on_branch("to-valid", junk, valid, "restore to the first well-formed text")
        self.on_branch("to-junk", junk, "no heading\n", "back to junk")
        self.assert_restoration(check.evaluate("main", "to-valid", self.repo))
        self.assert_edit(check.evaluate("main", "to-junk", self.repo))

    def test_a_never_well_formed_file_cannot_be_restored_only_removed(self):
        junk = self.repo / "entries" / "20260102-000000-j.md"
        self.commit(junk, "no heading\n", "junk lands")
        self.commit(junk, "still no heading\n", "junk changes")
        self.on_branch("back", junk, "no heading\n", "back to the earlier junk")
        self.assert_edit(check.evaluate("main", "back", self.repo))
        self.remove_on_branch("tidy", junk)
        self.assert_tidying(check.evaluate("main", "tidy", self.repo))

    def test_a_file_whose_name_is_not_an_entry_name_has_no_original(self):
        # such a file only gets onto main by a direct push; it can be tidied away, not "restored"
        notes = self.repo / "entries" / "notes.md"
        text = "### 2026-01-03 00:00 UTC · n · note\n\nwell-formed text under a name that is not an entry name\n"
        self.commit(notes, text, "lands")
        self.commit(notes, text.replace("well-formed", "changed"), "changes")
        self.on_branch("back", notes, text, "back to its first text")
        self.assert_edit(check.evaluate("main", "back", self.repo))
        self.remove_on_branch("tidy", notes)
        self.assert_tidying(check.evaluate("main", "tidy", self.repo))

    def test_a_version_that_is_not_text_is_passed_over(self):
        # the file's first version is not UTF-8; the walk must step past it to the well-formed text
        damaged = self.repo / "entries" / "20260102-000000-d.md"
        valid = "### 2026-01-02 00:00 UTC · d · note\n\nreal\n"
        self.commit(damaged, NOT_TEXT, "lands as bytes that are not text")
        self.commit(damaged, valid, "made well-formed")
        self.commit(damaged, valid.replace("real", "changed"), "tampered")
        self.on_branch("to-valid", damaged, valid, "restore")
        self.on_branch("to-bytes", damaged, NOT_TEXT, "back to the bytes")
        self.assert_restoration(check.evaluate("main", "to-valid", self.repo))
        self.assert_edit(check.evaluate("main", "to-bytes", self.repo))

    def test_reverting_damage_that_is_not_text_is_a_restoration(self):
        self.commit(self.entry, NOT_TEXT, "damage that is not UTF-8")
        self.commit(self.entry, FIRST, "the revert")
        self.assert_restoration(check.evaluate("main~1", "main", self.repo))

    def test_a_novel_text_is_still_an_edit(self):
        self.on_branch("novel", self.entry, FIRST.replace("first", "novel"), "edit")
        self.assert_edit(check.evaluate("main", "novel", self.repo))

    def test_git_output_is_utf8_whatever_the_locale(self):
        # a verdict must not depend on the environment the check runs in: the heading's middle dot
        # is not ASCII, and the same bytes must read the same under a locale that cannot spell it
        blob = self.git("rev-parse", "main:entries/20260101-000000-a.md")
        code = (
            "import locale, pathlib, sys\n"
            f"sys.path.insert(0, {str(pathlib.Path(check.__file__).resolve().parent)!r})\n"
            "import check\n"
            "print(locale.getpreferredencoding(False), flush=True)\n"
            f"text = check.git('cat-file', 'blob', {blob!r}, cwd=pathlib.Path({str(self.repo)!r}))\n"
            "sys.stdout.buffer.write(text.encode('utf-8'))\n"
        )
        env = {k: v for k, v in os.environ.items() if not k.startswith("LC_") and k != "LANG" and k != "LANGUAGE"}
        env["LC_ALL"] = "C"
        child = subprocess.run([sys.executable, "-I", "-X", "utf8=0", "-c", code], env=env, capture_output=True)
        self.assertEqual(child.returncode, 0, child.stderr.decode("utf-8", "replace"))
        encoding, _, text = child.stdout.partition(b"\n")
        if encoding.decode("ascii").lower().replace("_", "-") in ("utf-8", "utf8"):
            self.skipTest("could not get a locale that is not UTF-8 on this machine")
        self.assertEqual(text.decode("utf-8"), FIRST)


if __name__ == "__main__":
    unittest.main()
