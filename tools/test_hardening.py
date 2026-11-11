"""Tests for the reflex's token: how the checkouts keep it, and what the one push to main is given.

Run: python3 -m unittest discover -s tools

The reflex's job holds a token that can write to the repository. No checkout may leave it in
.git/config, and the push that needs it gets it through the environment of that push only.
"""
from __future__ import annotations

import base64
import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import consolidate  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
