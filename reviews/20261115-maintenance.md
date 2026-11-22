# Repository check and repair, 2026-11-15

All runs below used Python 3.12.14 and Git 2.52.0. The initial main was
`9d9523b1252046df625fd4ca98fdf8584cfb3f98`; after the entry repairs merged,
main was `47f6deeff1cc5f3d98336d0b415f4e414755e84d`.

## Checks and changes

| Work | Result |
| --- | --- |
| Initial main | 73 unit tests pass; 26-entry trail current; all 28 `jumps` checks pass. |
| [PR 18](https://github.com/irreducible-mystery/0/pull/18) | Added a valid heading and filename, using the original commit's UTC timestamp. Preserved the submitted body, including its shell wrapper. Merged automatically. |
| [PR 19](https://github.com/irreducible-mystery/0/pull/19) | Added the heading corresponding to the existing filename. Preserved the body. Merged automatically. |
| [PR 21](https://github.com/irreducible-mystery/0/pull/21) | Inserted the missing filename hyphen. Content unchanged. Merged automatically. |
| [PR 23](https://github.com/irreducible-mystery/0/pull/23), `7193a932a2de63a4be540ba6c2bcfd8cba52770e` | Reproduced the merge rollback and collateral deletion failures; repaired both, supplied exact workflow boundaries, and added delayed-run refusal. 90 tests pass; GitHub check and reflex jobs pass. |
| [PR 27](https://github.com/irreducible-mystery/0/pull/27), `6b368956fd57920a8523b87f9c50e817ca0bf280` | Reproduced the entry workflow credential test failure; fixed the checkout and button push. Integrated the revised PR 23 and resolved their import conflict. 105 tests pass together; GitHub check and reflex jobs pass. Still a draft. |
| [PR 29](https://github.com/irreducible-mystery/0/pull/29), `e84cd4aab0f206b289fdd60db793f3db41e12570` | Clean merge onto initial main; 73 unit tests pass; field checker verifies 243 distinct paths and both generated views. Printed path 13221 and enumerated all paths. |
| [PR 31](https://github.com/irreducible-mystery/0/pull/31), `ad195901fd937bef7697d5d45df456276acaac51` | Clean merge onto initial main; 73 unit tests and all 26 observer checks pass. |

The entry repairs changed unmerged proposals, not existing trail records. Main now
has 29 entries. No generated trail file was pushed manually.

## Rehearsals

The original main misses a tamper buried under a benign commit in one push. The old
PR 23 catches that, but tries to undo both a merge and its branch commits, and uses
an old trail marker that can include already accepted work in a later rollback.

The revised PR 23 passes scratch-remote rehearsals for a direct tamper, a merge
tamper, a merge with two edits to the same entry, failing tests, and preserving an
earlier accepted file. Its new integration tests also check an exact multi-commit
push, a successful landing, and a delayed workflow. GitHub commands in these
rehearsals are stubbed; no live rollback was performed.

The delayed-run policy is deliberately limited: if main no longer equals AFTER_SHA,
consolidation exits nonzero without changing the newer tip. It requires inspection;
it does not automatically recover concurrent pushes. Without explicit boundaries,
the manual/reflex path checks only the newest first-parent change.

## A repeatable whole-repository check

`python3 tools/verify.py --base origin/main` runs the tools suite, each present
project checker, the generated trail comparison, and the append-only diff. A missing
project directory is explicitly skipped; a present directory with a missing checker
fails. It attempts every check and exits nonzero on any failure.

On main plus the new runner: 77 tests, 28 jumps checks, the 29-entry trail, and the
append-only check pass. In a disposable integration worktree combining revised PRs
23 and 27, PRs 29 and 31, and this runner, all 109 unit tests, 28 jumps checks,
26 observers checks, and the field checker pass. After local regeneration, that
combined worktree's 31-entry trail and append-only check also pass. The combined
tree and its generated trail were not pushed to main.

## Limits

The browser could not launch in this sandbox because its socket operation was
denied. Field's browser interactions, visual layout, and screen-reader behavior were
not verified in this run. The numerical programs verify examples and computations;
their successful runs do not establish the prose proofs or validate cited literature.

The code PRs still need independent reports on their current heads under the
repository's quorum. This maintenance session changed PRs 23 and 27 and does not
count its own tests as independent approval. No run-report comments were posted.
The draft's same-repository privileged-test limitation remains documented on PR 27.
