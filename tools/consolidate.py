"""Consolidate main after something lands on it: keep what held up, undo what did not.

    python3 tools/consolidate.py

Looks at what the push onto origin/main added. If the range changed the trail in a way the
trail does not allow, or the tests fail on it, the whole range is reverted as one new commit
(history is kept) and the pull request it came from, if any, gets a comment saying why.
Otherwise TRAIL.md is regenerated from entries/ and committed if it changed. Its own commits
are skipped, so it cannot loop.

A direct push can carry several commits; checking only the newest would let a tamper in an
earlier commit of the same push survive, because the newest commit alone can be clean. The
range starts at GitHub's `before` when the workflow passes it (BEFORE_SHA), paired with
AFTER_SHA so a delayed workflow cannot widen the range. If main has moved, it stops for
review; it does not retry against a wider range. Without a boundary it checks only the
newest first-parent change, as for a single merge. No trail marker is used as a boundary.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

# Validation must not dirty tracked bytecode in an unusual checkout.
sys.dont_write_bytecode = True
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

ROOT = check.ROOT
BOT = "github-actions[bot]"


def sh(*args: str, check_=True, cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=check_, capture_output=True, text=True)


def push_base(head: str, parents: list[str], cwd: pathlib.Path = ROOT) -> str | None:
    """Use the supplied push boundary, or only the newest first-parent change.

    A trail regeneration is not a landing marker: accepted code-only changes may
    have followed it. Never infer a wider rollback from its author or subject.
    An explicit boundary must be on this head's first-parent chain.
    """
    before = os.environ.get("BEFORE_SHA", "").strip()
    if before and set(before) != {"0"}:
        chain = sh("git", "rev-list", "--first-parent", head, cwd=cwd).stdout.split()
        if before not in chain[1:]:
            raise ValueError("BEFORE_SHA must precede the landing on its first-parent chain")
        return before
    return parents[0] if parents else None


def revert_range(base: str | None, head: str, cwd: pathlib.Path = ROOT) -> tuple[bool, str]:
    """Revert every commit in base..head as one new commit, newest first. Returns (ok, error).

    Reverting only the newest commit would leave an earlier commit of the same push in place,
    which is the whole point of checking the range. On any conflict the sequence is aborted and
    the tree is left as it was, so the caller can open an issue instead of pushing a half-revert.
    """
    # Tests may leave untracked bytecode. Git's revert protects untracked files;
    # refuse tracked edits so aborting our sequence cannot discard local work.
    if sh("git", "status", "--porcelain", "--untracked-files=no", cwd=cwd).stdout.strip():
        return False, "the checkout is not clean; no rollback attempted"
    start = sh("git", "rev-parse", "HEAD", cwd=cwd).stdout.strip()
    if start != head:
        return False, "the checkout moved beyond the landing; no rollback attempted"
    if base:
        chain = sh("git", "rev-list", "--first-parent", head, cwd=cwd).stdout.split()
        if base not in chain[1:]:
            return False, "the rollback base is not a first-parent ancestor"
        commits = sh("git", "rev-list", "--first-parent", "--reverse", f"{base}..{head}", cwd=cwd).stdout.split()
    else:
        commits = [head]
    for commit in reversed(commits):
        parent_count = len(sh("git", "rev-list", "--parents", "-n", "1", commit, cwd=cwd).stdout.split()) - 1
        args = ["git", "revert", "--no-commit"] + (["-m", "1"] if parent_count > 1 else []) + [commit]
        r = sh(*args, check_=False, cwd=cwd)
        if r.returncode != 0:
            sh("git", "revert", "--abort", check_=False, cwd=cwd)
            sh("git", "reset", "--hard", start, cwd=cwd)
            return False, (r.stderr or r.stdout)[-1500:]
    sh("git", "revert", "--quit", check_=False, cwd=cwd)
    if sh("git", "diff", "--cached", "--quiet", check_=False, cwd=cwd).returncode == 0:
        return True, ""  # every commit in the range was already a no-op
    subject = f"Revert the push {base[:7]}..{head[:7]}" if base else f"Revert {head[:7]}"
    r = sh("git", "commit", "-q", "-m", subject, check_=False, cwd=cwd)
    if r.returncode != 0:
        sh("git", "reset", "--hard", start, cwd=cwd)
        return False, (r.stderr or r.stdout)[-1500:]
    return True, ""


def push_main() -> bool:
    for _ in range(2):
        r = sh("git", "push", "origin", "HEAD:main", check_=False)
        if r.returncode == 0:
            return True
        print(f"consolidate: push rejected: {r.stderr.strip()[-300:]}")
        sh("git", "fetch", "-q", "origin", "main")
        # someone else pushed first: our commit is a revert or a regeneration, both of which are
        # cheap to redo, so drop ours and let the next run (or the caller) start over
        return False
    return False


def comment_on_pr(subject: str, text: str) -> None:
    m = re.search(r"#(\d+)", subject)
    if not m:
        return
    sh("gh", "api", "-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{m.group(1)}/comments", "-f", f"body={text}", check_=False)


def main(argv=None) -> int:
    sh("git", "fetch", "-q", "origin", "main")
    sh("git", "checkout", "-q", "--detach", "origin/main")
    head = sh("git", "rev-parse", "HEAD").stdout.strip()
    expected = os.environ.get("AFTER_SHA", "").strip()
    if os.environ.get("BEFORE_SHA", "").strip() and not expected:
        print("consolidate: BEFORE_SHA requires AFTER_SHA; no changes made")
        return 1
    if expected and head != expected:
        print(f"consolidate: main moved beyond landing {expected[:7]}; no changes made. "
              "Review the original landing before retrying; its boundary was not widened.")
        return 1
    subject = sh("git", "log", "-1", "--format=%s").stdout.strip()
    author = sh("git", "log", "-1", "--format=%an").stdout.strip()
    parents = sh("git", "log", "-1", "--format=%P").stdout.split()
    if author == BOT and subject.startswith("trail:"):
        print("consolidate: newest commit is my own regeneration; nothing to do")
        return 0
    if author == BOT and subject.startswith("Revert"):
        print("consolidate: newest commit is my own revert; nothing to do")
        return 0

    problems: list[str] = []
    try:
        base = push_base(head, parents)
    except ValueError as e:
        print(f"consolidate: {e}; no changes made")
        return 1
    if base:
        result = check.evaluate(base, head)
        problems += result["problems"]
    t = subprocess.run([sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"],
                       cwd=ROOT, capture_output=True, text=True, timeout=600)
    if t.returncode != 0:
        problems.append("tests fail on main:\n```\n" + (t.stderr or t.stdout)[-2000:] + "\n```")

    if problems:
        print(f"consolidate: main is red at {head[:7]}; reverting {base[:7] if base else 'it'}")
        ok, err = revert_range(base, head)
        text = "\n".join(f"- {p}" for p in problems)
        if not ok:
            print(f"consolidate: rollback stopped: {err}")
            sh("gh", "issue", "create", "--title", f"reflex: main is red at {head[:7]} and could not be reverted",
               "--body", f"`{subject}`\n\n{text}\n\n```\n{err}\n```", check_=False)
            return 1
        if not push_main():
            return 1
        comment_on_pr(subject, f"reflex: after merging, main was red, so the landing "
                      f"(`{base[:7] if base else head[:7]}..{head[:7]}`) was reverted as one new commit; "
                      f"history is kept:\n{text}\n\nFix on the branch and open it again.")
        return 0

    a = subprocess.run([sys.executable, "-B", "tools/assemble.py"], cwd=ROOT, capture_output=True, text=True)
    print(a.stdout.strip() or a.stderr.strip())
    if a.returncode != 0:
        return 1
    if not sh("git", "status", "--porcelain", "TRAIL.md").stdout.strip():
        print("consolidate: TRAIL.md already current")
        return 0
    n = sum(1 for p in (ROOT / "entries").iterdir() if p.suffix == ".md" and p.name != "README.md")
    sh("git", "add", "TRAIL.md")
    sh("git", "commit", "-q", "-m", f"trail: {n} entries")
    return 0 if push_main() else 1


if __name__ == "__main__":
    sys.exit(main())
