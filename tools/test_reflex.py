"""Tests for the reflex's merge step. Run: python3 -m unittest discover -s tools

The merge names the head whose tests and run reports the reflex counted. If a push lands after
the reflex fetched and tested a head, the merge must refuse rather than take the newer head on
the strength of reports for the older one.
"""
from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import reflex  # noqa: E402

HEAD = "0123456789abcdef0123456789abcdef01234567"


def gh_result(code: int) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout="", stderr="pull request head changed")


class MergeTests(unittest.TestCase):
    def test_the_merge_names_the_head_that_was_checked(self):
        with patch.object(reflex, "sh", return_value=gh_result(0)) as sh, \
                patch.object(reflex, "say"), patch.object(reflex.consolidate, "main"), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reflex.merge(7, HEAD, "a title", "why"), "merged")
        args = sh.call_args.args
        self.assertIn("--match-head-commit", args)
        self.assertEqual(args[args.index("--match-head-commit") + 1], HEAD)

    def test_a_head_that_moved_is_not_merged(self):
        with patch.object(reflex, "sh", return_value=gh_result(1)), \
                patch.object(reflex, "say") as say, patch.object(reflex.consolidate, "main") as consolidate, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reflex.merge(7, HEAD, "a title", "why"), "merge failed")
        consolidate.assert_not_called()
        say.assert_called_once()


if __name__ == "__main__":
    unittest.main()
