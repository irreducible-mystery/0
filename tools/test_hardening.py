"""Tests for the reflex's token: how the checkouts keep it, and what the one push to main is given.

Run: python3 -m unittest discover -s tools

The reflex's job holds a token that can write to the repository. No checkout may leave it in
.git/config, and the push that needs it gets it through the environment of that push only.
"""
from __future__ import annotations

import base64
import contextlib
import io
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import consolidate  # noqa: E402
import reflex  # noqa: E402

WORKFLOWS = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows"


HEADER = "http.https://github.com/.extraheader"


def header_of(env: dict[str, str]) -> str | None:
    """The value git will be given for the header, found by its key among the GIT_CONFIG_* entries."""
    for i in range(int(env.get("GIT_CONFIG_COUNT") or 0)):
        if env.get(f"GIT_CONFIG_KEY_{i}") == HEADER:
            return env[f"GIT_CONFIG_VALUE_{i}"]
    return None


class PushTests(unittest.TestCase):
    def test_the_token_reaches_the_push_as_a_header(self):
        with mock.patch.dict(os.environ, {"GH_TOKEN": "token-for-test"}):
            value = header_of(consolidate.push_env())
        self.assertIsNotNone(value)
        self.assertTrue(value.startswith("AUTHORIZATION: basic "))
        basic = value.rsplit(" ", 1)[1]
        self.assertEqual(base64.b64decode(basic).decode(), "x-access-token:token-for-test")

    def test_the_header_is_added_after_git_configuration_already_there(self):
        preset = {"GH_TOKEN": "token-for-test", "GIT_CONFIG_COUNT": "2",
                  "GIT_CONFIG_KEY_0": "a.b", "GIT_CONFIG_VALUE_0": "1",
                  "GIT_CONFIG_KEY_1": "c.d", "GIT_CONFIG_VALUE_1": "2"}
        with mock.patch.dict(os.environ, preset):
            env = consolidate.push_env()
        self.assertEqual(env["GIT_CONFIG_COUNT"], "3")
        self.assertEqual((env["GIT_CONFIG_KEY_0"], env["GIT_CONFIG_KEY_1"]), ("a.b", "c.d"))
        self.assertEqual(env["GIT_CONFIG_KEY_2"], HEADER)

    def test_without_a_token_the_push_gets_the_environment_unchanged(self):
        with mock.patch.dict(os.environ, {}):
            os.environ.pop("GH_TOKEN", None)
            before = dict(os.environ)
            env = consolidate.push_env()
        # assertTrue, so that a failure does not print the whole environment
        self.assertTrue(env == before)


class WorkflowTests(unittest.TestCase):
    def test_no_checkout_keeps_its_credentials_on_disk(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            with self.subTest(workflow=path.name):
                self.assertEqual(text.count("persist-credentials: false"), text.count("uses: actions/checkout@"))

    def test_a_comment_wakes_the_reflex_only_from_someone_who_can_write(self):
        text = (WORKFLOWS / "reflex.yml").read_text(encoding="utf-8")
        self.assertIn('"OWNER","MEMBER","COLLABORATOR"', text)
        self.assertIn("github.event.comment.author_association", text)


REPO_NAME = "irreducible-mystery/0"
HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"


def pull(head_repo: str | None) -> dict:
    """A pull request as the API returns it; head_repo is the full name of its head repository."""
    repo = None if head_repo is None else {"full_name": head_repo}
    return {"state": "open", "draft": False, "title": "a change", "body": "by: someone",
            "user": {"login": "someone"}, "head": {"sha": HEAD_SHA, "repo": repo}}


def checked(other: int = 0, entries_added: int = 0, entries_only: bool = False) -> dict:
    """What check.evaluate returns for a merge with this many changes."""
    return {"ok": True, "entries_added": entries_added, "entries_restored": 0, "other_changes": other,
            "entries_only": entries_only, "problems": []}


def fake_sh(*args, **kwargs):
    """Stands in for the reflex's git calls: rev-parse gives the head; the rest do nothing."""
    stdout = HEAD_SHA if args[:2] == ("git", "rev-parse") else ""
    return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")


class ForkCodeTests(unittest.TestCase):
    def look(self, pr: dict, result: dict):
        tests = mock.MagicMock(return_value=(True, ""))
        with mock.patch.object(reflex, "REPO", REPO_NAME), \
                mock.patch.object(reflex, "gh_json", return_value=pr), \
                mock.patch.object(reflex, "sh", side_effect=fake_sh), \
                mock.patch.object(reflex.check, "evaluate", return_value=result), \
                mock.patch.object(reflex, "run_tests_in", tests), \
                mock.patch.object(reflex, "say") as say, \
                mock.patch.object(reflex, "reports", return_value={}), \
                mock.patch.object(reflex, "merge", return_value="merged") as merge, \
                contextlib.redirect_stdout(io.StringIO()):
            outcome = reflex.look(7)
        return outcome, tests, say, merge

    def test_a_fork_that_changes_code_is_not_run_here(self):
        outcome, tests, say, merge = self.look(pull("someone/0"), checked(other=1))
        self.assertEqual(outcome, "fork: not run here")
        tests.assert_not_called()
        merge.assert_not_called()
        self.assertEqual(say.call_args.args[2], "fork")

    def test_a_fork_that_only_adds_entries_is_run_and_merged(self):
        outcome, tests, say, merge = self.look(pull("someone/0"), checked(entries_added=1, entries_only=True))
        tests.assert_called_once()
        self.assertEqual(outcome, "merged")

    def test_a_fork_whose_repository_is_gone_counts_as_a_fork(self):
        outcome, tests, say, merge = self.look(pull(None), checked(other=1))
        self.assertEqual(outcome, "fork: not run here")
        tests.assert_not_called()

    def test_a_pull_request_from_this_repository_is_run_as_before(self):
        outcome, tests, say, merge = self.look(pull(REPO_NAME), checked(other=1))
        tests.assert_called_once()
        self.assertTrue(outcome.startswith("waiting"), outcome)


if __name__ == "__main__":
    unittest.main()
