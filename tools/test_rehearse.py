"""Tests for the rehearsal. Run: python3 -m unittest discover -s tools

Asserted here are the things current main does: it reverts a change that broke the trail or a
test, and a revert takes back exactly what it reverts, and no more. The scenarios that show a gap
(whole_push, lost_race, and what a revert takes with it in collateral) are reported by the script
and not asserted, because their current result is what the rehearsal exists to show.
"""
from __future__ import annotations

import functools
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import rehearse  # noqa: E402


@functools.lru_cache(maxsize=None)
def outcome(name: str) -> rehearse.Outcome:
    return rehearse.run(name)


class RevertTests(unittest.TestCase):
    def test_a_direct_push_that_changes_an_entry_is_reverted(self):
        self.assertEqual(outcome("revert_commit").verdict, "reverted")

    def test_a_merge_that_changes_an_entry_is_reverted_and_leaves_main_as_it_was(self):
        result = outcome("revert_merge")
        self.assertEqual(result.verdict, "reverted")
        self.assertEqual(result.differs_from_before, [])

    def test_a_merge_of_two_edits_to_one_entry_is_reverted_and_leaves_main_as_it_was(self):
        result = outcome("revert_merge_two_edits")
        self.assertEqual(result.verdict, "reverted")
        self.assertEqual(result.differs_from_before, [])

    def test_a_merge_that_adds_a_red_test_is_reverted(self):
        self.assertEqual(outcome("red_tests").verdict, "reverted")

    def test_the_comment_consolidate_would_post_goes_to_the_stub(self):
        # revert_merge's subject names a pull request, so consolidate comments on it: once
        self.assertEqual(outcome("revert_merge").gh_calls, 1)


if __name__ == "__main__":
    unittest.main()
