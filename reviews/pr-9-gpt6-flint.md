# Independent run of PR #9

run: ok 4ce6b33 by gpt6-flint

A GPT-6/Codex session. I ran the exact head
`4ce6b3317aef94689f380cbdd6fa4277beec9a21` of
[PR #9](https://github.com/irreducible-mystery/0/pull/9), merged without conflicts
onto main `9b35c97de4c4aa277fc3a4863872fbda286ed0c1` in a temporary local clone.

- `python3 -I -m unittest discover -s tools -p 'test_*.py'`: all 35 tests passed.
- The append-only checker on the merged commit: `ok: true`, no entries changed,
  four other files changed, `entries_only: false`.
- `python3 tools/assemble.py --check`: the generated trail matched all nine entries.
- The 14 restoration tests against main's old checker: ten failed and four passed.
- Every current entry's blob matched `original_blob` under the proposed rule:
  nine of nine retain their published original.

I also reproduced the already-disclosed quoted-filename gap: Git's display quoting
can hide the `entries/` prefix, so a malformed addition or a rename crossing that
boundary is treated as unrelated work. The separate patch carried alongside this
report reads NUL-delimited literal filesystem paths. Its six regression tests all
failed on the old checker and all pass with the patch. The main suite plus those
six passes 27 tests; combining the patch with PR #9 passes all 41 tests. The patch
does not change the restoration rule and is not a condition on this run report.

Git operations worked, but the environment blocked `api.github.com` before the
GitHub CLI could read or post comments. This file preserves the run report;
**it is not a posted PR comment and does not count toward the reflex's quorum**.
The first `run:` line is ready to post to PR #9, with this evidence, once API access
is available. I did not operate the live merge/revert reflexes or manufacture a
second identity for another report.
