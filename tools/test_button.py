"""The button writes an entry by the same rules as tools/entry.py, puts it on main, and says what
is on main afterwards rather than what it meant to do."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import button  # noqa: E402
import check  # noqa: E402

WHEN = dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc)
HEADING = "### 2026-01-02 03:04 UTC · owner · note"
GH006 = "GH006: Protected branch update failed for refs/heads/main."


class ParagraphTests(unittest.TestCase):
    def test_slashes_with_spaces_start_a_paragraph_and_links_are_left_alone(self):
        self.assertEqual(button.paragraphs("one two // three   four //  // five"), "one two\n\nthree four\n\nfive")
        self.assertEqual(button.paragraphs("see https://example.org/x // and that"), "see https://example.org/x\n\nand that")
        self.assertEqual(button.paragraphs("   plain   "), "plain")
        self.assertEqual(button.paragraphs(""), "")


class WordingTests(unittest.TestCase):
    def test_an_author_name_is_what_git_will_take(self):
        self.assertEqual(button.author_name("owner"), "owner")
        self.assertEqual(button.author_name("'owner'"), "owner")
        self.assertEqual(button.author_name("<b>x</b>\x7f"), "bx/b")
        self.assertEqual(button.author_name(","), "anon")  # git refuses a name of nothing but punctuation
        self.assertEqual(button.author_name("Dr."), "Dr.")  # git keeps periods, so the button does too
        self.assertEqual(button.author_name("..."), "...")
        self.assertEqual(button.author_name("Jürgen 🌊"), "Jürgen 🌊")

    def test_a_refusal_quotes_the_far_end_and_not_the_hints(self):
        stderr = (f"remote: {GH006}\nTo github.com:o/r.git\n ! [remote rejected] HEAD -> main (pre-receive hook declined)\n"
                  "error: failed to push some refs to 'github.com:o/r.git'\n")
        self.assertEqual(button.refusal(stderr), GH006 + " ! [remote rejected] HEAD -> main (pre-receive hook declined)")
        self.assertEqual(button.refusal("fatal: unable to access 'x': 403\nhint: try later\n"), "fatal: unable to access 'x': 403")
        self.assertEqual(button.sentence("said so."), "said so.")
        self.assertEqual(button.sentence("said so"), "said so.")


class ButtonTests(unittest.TestCase):
    """A clone of a bare remote, as the workflow's checkout is: origin/main exists, main holds an entry."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = pathlib.Path(tmp.name)
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            self.summary_path = f.name
        self.addCleanup(os.unlink, self.summary_path)
        # a page of our own: consolidate runs this suite inside a real run, with the real page in the environment
        env = patch.dict(os.environ, {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                                      "GIT_COMMITTER_EMAIL": "t@t", "GITHUB_STEP_SUMMARY": self.summary_path})
        env.start()
        self.addCleanup(env.stop)
        self.remote = base / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True)
        self.repo = base / "clone"
        subprocess.run(["git", "clone", "-q", str(self.remote), str(self.repo)], check=True, capture_output=True)
        (self.repo / "entries").mkdir()
        (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nfirst\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "first entry")
        self.git("push", "-q", "origin", "main")

    def git(self, *args: str, cwd: pathlib.Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True, capture_output=True, encoding="utf-8").stdout.strip()

    def remote_main(self) -> str:
        return self.git("ls-remote", "origin", "refs/heads/main").split()[0]

    def entries_on_main(self) -> list[str]:
        self.git("fetch", "-q", "origin", "main")
        return self.git("ls-tree", "--name-only", "origin/main", "entries/").split()

    def another_clone(self) -> pathlib.Path:
        other = self.repo.parent / "other"
        if not other.exists():
            subprocess.run(["git", "clone", "-q", str(self.remote), str(other)], check=True, capture_output=True)
        return other

    def push_from(self, other: pathlib.Path, fname: str, content: str, ref: str = "main") -> str:
        (other / "entries" / fname).write_text(content, encoding="utf-8")
        self.git("add", "-A", cwd=other)
        self.git("commit", "-qm", "another entry", cwd=other)
        self.git("push", "-q", "origin", f"HEAD:refs/heads/{ref}", cwd=other)
        return self.git("rev-parse", "HEAD", cwd=other)

    def hook(self, script: str) -> None:
        path = self.remote / "hooks" / "pre-receive"
        path.write_text("#!/bin/sh\n" + script, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def press(self, text: str = "trying again", argv=(), **env) -> tuple[int, str]:
        """button.main as the workflow runs it; returns (exit code, summary page)."""
        values = {"ENTRY_NAME": "owner", "ENTRY_KIND": "note", "ENTRY_TEXT": text, "GITHUB_STEP_SUMMARY": self.summary_path, **env}
        with patch.dict(os.environ, values), contextlib.redirect_stdout(io.StringIO()):  # the page is read, not the log
            code = button.main(list(argv), self.repo)
        return code, pathlib.Path(self.summary_path).read_text(encoding="utf-8")

    def test_the_entry_lands_on_its_own_branch_as_an_entries_only_change(self):
        branch, fname = button.write_entry("owner", "note", "hello to all // it is, it is not", WHEN, self.repo)
        self.assertEqual(branch, "entry/20260102-030405-owner")
        self.assertEqual(fname, "20260102-030405-owner.md")
        self.assertEqual(self.git("branch", "--show-current"), branch)
        self.assertEqual((self.repo / "entries" / fname).read_text(encoding="utf-8"),
                         HEADING + "\n\nhello to all\n\nit is, it is not\n")
        # the typed name, at an address that is nobody's; the committer is whoever runs the button
        self.assertEqual(self.git("log", "-1", "--format=%an <%ae> | %cn | %s"), "owner <owner@button.invalid> | t | entry: owner note")
        result = check.evaluate("origin/main", "HEAD", self.repo)
        self.assertTrue(result["entries_only"], result)

    def test_the_subject_has_the_kind_as_the_heading_has_it_and_no_pull_request_number_and_odd_names_commit(self):
        _, fname = button.write_entry("Owner #7", "Note", "hello", WHEN, self.repo)
        self.assertEqual((self.repo / "entries" / fname).read_text(encoding="utf-8").split("\n")[0], "### 2026-01-02 03:04 UTC · Owner #7 · note")
        self.assertEqual(self.git("log", "-1", "--format=%s"), "entry: Owner 7 note")  # "#7" would read as a pull request to the reflex
        self.git("checkout", "-q", "main")
        _, fname = button.write_entry(",", "note", "hello", WHEN.replace(second=6), self.repo)
        self.assertEqual(fname, "20260102-030406-anon.md")
        self.assertEqual(self.git("log", "-1", "--format=%an <%ae>"), "anon <anon@button.invalid>")
        self.git("checkout", "-q", "main")
        button.write_entry("Dr.", "note", "hello", WHEN.replace(second=7), self.repo)
        self.assertEqual(self.git("log", "-1", "--format=%an"), "Dr.")

    def test_a_missing_name_or_text_is_refused_in_plain_words_before_anything_is_written(self):
        with self.assertRaises(ValueError) as e:
            button.write_entry("  ", "note", "hello", WHEN, self.repo)
        self.assertIn("a name is needed", str(e.exception))
        with self.assertRaises(ValueError) as e:
            button.write_entry("owner", "note", " // ", WHEN, self.repo)
        self.assertIn("needs a body", str(e.exception))
        with self.assertRaises(ValueError) as e:
            button.write_entry("owner", "Question?", "hello", WHEN, self.repo)
        self.assertIn("one short word", str(e.exception))
        self.assertNotIn("lowercase", str(e.exception))  # capitals are taken, so they are not asked about
        with self.assertRaises(ValueError):
            button.write_entry("owner", "note", "a // ### b", WHEN, self.repo)
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual(self.git("status", "--porcelain"), "")
        (self.repo / "stray.txt").write_text("not committed\n", encoding="utf-8")
        with self.assertRaises(ValueError) as e:
            button.write_entry("owner", "note", "hello", WHEN, self.repo)
        self.assertIn("uncommitted changes", str(e.exception))

    def test_the_entry_is_pushed_to_main_and_main_moving_in_between_is_rebased_over(self):
        button.write_entry("owner", "note", "hello to all", WHEN, self.repo)
        sha = button.push_to_main(self.repo)
        self.assertEqual(self.remote_main(), sha)
        # a second entry while someone else lands one first
        self.push_from(self.another_clone(), "20260103-000000-b.md", "### 2026-01-03 00:00 UTC · b · note\n\nfirst\n")
        self.git("checkout", "-q", "main")
        button.write_entry("owner", "note", "and again", WHEN.replace(minute=5), self.repo)
        with patch.object(button.time, "sleep"):
            sha = button.push_to_main(self.repo)
        self.assertEqual(self.remote_main(), sha)
        self.assertEqual(self.entries_on_main(), ["entries/20260101-000000-a.md", "entries/20260102-030405-owner.md",
                                                  "entries/20260102-030505-owner.md", "entries/20260103-000000-b.md"])

    def test_main_moving_while_the_push_is_being_received_is_rebased_over_too(self):
        # another writer's commit, parked on the remote, is put on main by a hook while the button's
        # first push is being received: git refuses in other words than a plain non-fast-forward
        parked = self.push_from(self.another_clone(), "20260103-000000-b.md", "### 2026-01-03 00:00 UTC · b · note\n\nfirst\n", ref="parked")
        self.hook(f"if [ ! -f raced ]; then touch raced; env -u GIT_QUARANTINE_PATH git update-ref refs/heads/main {parked}; fi\nexit 0\n")
        button.write_entry("owner", "note", "hello", WHEN, self.repo)
        with patch.object(button.time, "sleep"):
            sha = button.push_to_main(self.repo)
        self.assertEqual(self.remote_main(), sha)
        self.assertTrue((self.remote / "raced").exists())
        self.assertEqual(self.entries_on_main(), ["entries/20260101-000000-a.md", "entries/20260102-030405-owner.md",
                                                  "entries/20260103-000000-b.md"])

    def test_main_moving_every_time_is_given_up_on_after_five_tries(self):
        other = self.another_clone()
        count = iter(range(1, 9))

        def another_lands(*_) -> None:  # in place of the pause between tries
            n = next(count)
            self.push_from(other, f"20260103-00000{n}-b.md", f"### 2026-01-03 00:00 UTC · b · note\n\n{n}\n")

        button.write_entry("owner", "note", "hello", WHEN, self.repo)
        another_lands()
        with patch.object(button.time, "sleep", side_effect=another_lands) as sleep, self.assertRaises(ValueError) as e:
            button.push_to_main(self.repo)
        self.assertEqual(str(e.exception), "main kept moving under the button, 5 times over; press it again")
        self.assertEqual(sleep.call_count, 4)
        self.assertEqual(self.remote_main(), self.git("rev-parse", "HEAD", cwd=other))
        self.assertNotIn("entries/20260102-030405-owner.md", self.entries_on_main())

    def test_what_the_check_refuses_is_not_pushed(self):
        button.write_entry("owner", "note", "hello", WHEN, self.repo)
        before = self.remote_main()
        (self.repo / "entries" / "20260101-000000-a.md").write_text("### 2026-01-01 00:00 UTC · a · note\n\nchanged\n", encoding="utf-8")
        self.git("commit", "-qam", "and a change")
        with self.assertRaises(ValueError) as e:
            button.push_to_main(self.repo)
        self.assertIn("the check refused it", str(e.exception))
        self.assertIn("modified", str(e.exception))
        self.assertEqual(self.remote_main(), before)

    def test_a_refusal_that_is_not_main_moving_is_reported_once_as_it_came(self):
        self.hook(f"echo '{GH006}' >&2\nexit 1\n")
        button.write_entry("owner", "note", "hello", WHEN, self.repo)
        with patch.object(button.time, "sleep") as sleep, self.assertRaises(ValueError) as e:
            button.push_to_main(self.repo)
        sleep.assert_not_called()
        self.assertIn("refused, and not because of the entry", str(e.exception))
        self.assertTrue(str(e.exception).endswith("The words: " + GH006 + " ! [remote rejected] HEAD -> main (pre-receive hook declined)"), str(e.exception))
        self.assertNotIn("hint:", str(e.exception))

    def test_the_same_name_in_the_same_second_and_an_entry_already_there_are_told_apart(self):
        other = self.another_clone()
        button.write_entry("owner", "note", "mine", WHEN, self.repo)
        self.push_from(other, "20260102-030405-owner.md", HEADING + "\n\ntheirs\n")
        with patch.object(button.time, "sleep"), self.assertRaises(ValueError) as e:
            button.push_to_main(self.repo)
        self.assertIn("same name in the same second; press the button again", str(e.exception))
        self.assertEqual(self.git("status", "--porcelain"), "")  # the rebase was abandoned cleanly
        self.git("checkout", "-q", "main")
        button.write_entry("owner", "note", "twice", WHEN.replace(second=7), self.repo)
        self.push_from(other, "20260102-030407-owner.md", HEADING + "\n\ntwice\n")
        with patch.object(button.time, "sleep"), self.assertRaises(ValueError) as e:
            button.push_to_main(self.repo)
        self.assertIn("already on main", str(e.exception))

    def test_a_dry_run_writes_the_summary_and_pushes_nothing(self):
        before = self.remote_main()
        code, text = self.press(argv=["--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("> ### ", text)
        self.assertIn("> trying again", text)
        self.assertIn("Dry run", text)
        self.assertEqual(self.remote_main(), before)
        self.assertEqual(self.git("ls-remote", "--heads", "origin").count("\n") + 1, 1)  # only main on the remote

    def test_a_refusal_before_writing_keeps_the_typed_text_on_the_page_and_says_to_press_again(self):
        code, text = self.press("a long careful paragraph // and a second one", argv=["--dry-run"], ENTRY_KIND="Question?")
        self.assertEqual(code, 2)
        self.assertIn("Nothing was added: the kind must be one short word, such as note, question, reply, start or end. "
                      "Fix that and press the button again; what you typed is below.", text)
        self.assertIn("> name: owner\n> kind: Question?\n> text: a long careful paragraph // and a second one", text)
        code, text = self.press("   ", argv=["--dry-run"])
        self.assertIn("Nothing was added: an entry needs a body. Fix that and press the button again", text)

    def test_a_git_failure_is_on_the_summary_page_too(self):
        with patch.object(button, "author_name", return_value=","):
            code, text = self.press(argv=["--dry-run"])
        self.assertEqual(code, 2)
        self.assertIn("Nothing was added: `git commit` failed", text)
        self.assertIn("disallowed characters", text)
        self.assertIn("> text: trying again", text)

    # what the page says after the push comes from main itself, whatever consolidate did

    def regenerated_trail(self) -> tuple[int, str]:
        """A consolidate that regenerates the trail, as the real one does on a green main."""
        self.git("fetch", "-q", "origin", "main")
        self.git("checkout", "-q", "--detach", "origin/main")
        files = sorted(p for p in (self.repo / "entries").iterdir() if p.suffix == ".md")
        (self.repo / "TRAIL.md").write_text("# 0\n" + "".join("\n" + p.read_text(encoding="utf-8") for p in files), encoding="utf-8")
        self.git("add", "TRAIL.md")
        self.git("commit", "-qm", f"trail: {len(files)} entries")
        self.git("push", "-q", "origin", "HEAD:main")
        self.git("checkout", "-q", "main")  # HEAD is left behind, so what is read must be origin/main
        return 0, f"trail: {len(files)} entries"

    def reverted_entry(self) -> tuple[int, str]:
        """A consolidate that found main red and took the newest commit out again."""
        self.git("fetch", "-q", "origin", "main")
        self.git("checkout", "-q", "--detach", "origin/main")
        self.git("revert", "--no-edit", "HEAD")
        self.git("push", "-q", "origin", "HEAD:main")
        self.git("checkout", "-q", "main")
        return 0, "consolidate: main is red; reverting"

    def test_the_real_consolidate_runs_without_the_page_in_its_environment(self):
        seen = {}

        def fake_main(argv):
            seen["page"] = os.environ.get("GITHUB_STEP_SUMMARY")
            print("consolidate: TRAIL.md already current")
            return 0

        with patch.dict(sys.modules, {"consolidate": type(sys)("consolidate")}) as mods:
            mods["consolidate"].main = fake_main
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(button.run_consolidate(), (0, "consolidate: TRAIL.md already current"))
        self.assertIsNone(seen["page"])  # the tests consolidate runs would otherwise write the real page
        self.assertEqual(os.environ.get("GITHUB_STEP_SUMMARY"), self.summary_path)  # and it is back afterwards
        self.assertIn("consolidate: TRAIL.md already current", out.getvalue())  # the log keeps consolidate's words

    def test_the_summary_says_the_trail_is_regenerated_only_when_it_is(self):
        with patch.object(button, "run_consolidate", side_effect=self.regenerated_trail):
            code, text = self.press(GH_REPO="o/r")
        self.assertEqual(code, 0)
        self.assertIn("On main as `", text)
        self.assertIn("The trail is regenerated: https://github.com/o/r/blob/main/TRAIL.md.", text)
        self.assertIn("\n\ntrying again\n", self.git("show", "origin/main:TRAIL.md") + "\n")

    def test_the_summary_says_so_when_the_entry_was_taken_out_again(self):
        with patch.object(button, "run_consolidate", side_effect=self.reverted_entry):
            code, text = self.press(GH_REPO="o/r")
        self.assertEqual(code, 1)
        self.git("fetch", "-q", "origin", "main")
        revert = self.git("rev-parse", "origin/main")
        landed = self.git("rev-parse", "origin/main^")
        self.assertIn(f"It landed as `{landed[:7]}`, but main did not pass its tests with it, so the reflex took it out again "
                      f"(`{revert[:7]}`: https://github.com/o/r/commit/{revert}).", text)
        self.assertNotIn("regenerated", text)
        self.assertEqual(self.entries_on_main(), ["entries/20260101-000000-a.md"])

    def test_the_summary_says_so_when_the_trail_was_not_regenerated_and_quotes_consolidate(self):
        said = "consolidate: push rejected: ! [remote rejected] HEAD -> main (pre-receive hook declined)"
        with patch.object(button, "run_consolidate", return_value=(1, said)) as consolidate:
            code, text = self.press()
        self.assertEqual(code, 1)
        self.assertEqual(consolidate.call_count, 3)  # tried again, in case another writer got in first
        self.assertIn(f"The entry is on main, but the trail page does not show it yet: the consolidation after it stopped at `{said}`.", text)
        self.assertIn("Pressing again would add the entry a second time", text)
        self.assertNotIn("The trail is regenerated", text)
        self.assertEqual(len(self.entries_on_main()), 2)
        # consolidate finding nothing to do (someone else's revert on top) is reported the same way, without retries
        said = "consolidate: newest commit is my own revert; nothing to do"
        self.git("checkout", "-q", "main")
        with patch.object(button, "run_consolidate", return_value=(0, said)) as consolidate:
            code, text = self.press("once more", ENTRY_NAME="again")  # another name: the clock may still be on the same second
        self.assertEqual(code, 1)
        self.assertEqual(consolidate.call_count, 1)
        self.assertIn(f"stopped at `{said}`", text)

    def test_a_second_entry_in_the_same_minute_is_not_mistaken_for_the_first_on_the_trail(self):
        _, fname = button.write_entry("owner", "note", "first thought", WHEN, self.repo)
        button.push_to_main(self.repo)
        self.regenerated_trail()
        _, fname = button.write_entry("owner", "note", "second thought", WHEN.replace(second=9), self.repo)
        sha = button.push_to_main(self.repo)
        content = (self.repo / "entries" / fname).read_text(encoding="utf-8").rstrip("\n")
        with patch.object(button, "run_consolidate", return_value=(1, "consolidate: push rejected")), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(button.settle(sha, fname, content, self.repo, ""), 1)
        self.assertIn("does not show it yet", out.getvalue())
        self.assertNotIn("The trail is regenerated", out.getvalue())
        self.assertEqual(self.git("show", "origin/main:TRAIL.md").count(HEADING), 1)


if __name__ == "__main__":
    unittest.main()
